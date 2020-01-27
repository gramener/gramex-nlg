/* globals currentTemplateIndex, grammarOptions, templates, args, df, currentEventHandlers, nlg_base, g1 */
/* exported addToNarrative, setInitialConfig, checkTemplate, saveTemplate,
addCondition, addName, shareNarrative, copyToClipboard,
findAppliedInflections, checkSelection */
/* eslint-disable no-global-assign */
var narrative_name, dataset_name


class Template {
  // Class to hold a piece of text that gets rendered as a
  // tornado template when the narrative is invoked anywhere.
  constructor({text, tokenmap, fh_args, condition, name, template, previewHTML}) {
    this.text = text
    this.tokenmap = tokenmap
    this.fh_args = fh_args
    this.condition = condition
    this.name = name
    this.template = template
    this._previewHTML = previewHTML
  }

  previewHTML() {
    return this._previewHTML
  }
}

function hasTextSelection() {
  let sel = window.getSelection()
  if (sel.type != "Range") {
    return false
  }
  let siblings = sel.anchorNode.parentNode.childNodes
  let offset = 0
  let endOffset = 0
  for (let i=0; i<siblings.length; i++) {
    let sibling = siblings[i]
    if (!(sel.containsNode(sibling))) {
      offset += sibling.textContent.length
    } else {
      let range = sel.getRangeAt(0)
      endOffset = offset + range.endOffset
      offset += range.startOffset
      break
    }
  }
  return [offset, endOffset]

}

function hasClickedVariable(e) {
  let is_variable = false
  let tokenmap = templates[currentTemplateIndex].tokenmap
  let variable_ix = null
  for (let i=0; i < tokenmap.length; i++) {
    var token = tokenmap[i]
    let text = token.text
    if (e.target.innerText == text) {
      is_variable = true
      variable_ix = token.index
      break
    }
  }
  if (is_variable) {
    return variable_ix
  }
  return false
}

function checkSelection(e) {
  let clickedVar = hasClickedVariable(e)
  if (clickedVar || (clickedVar == 0)) {
    if (typeof(clickedVar) != "number") {
      clickedVar = clickedVar.join(',')
    }
    $.get(`${nlg_base}/variablesettings/${currentTemplateIndex}/${clickedVar}`).done(
      (e) => {
        $('#variable-settings').html(e)
      }
    )
  } else {
    let textSel = hasTextSelection()
    if (textSel) {
      let start, end
      [start, end] = textSel
      console.log(textSel, templates[currentTemplateIndex].text.slice(start, end))
    }
  }
}

function addToNarrative() {
  // Pick text from the input textarea, templatize, and add to the narrative.
  $.post(
    `${nlg_base}/textproc`,
    JSON.stringify({
      'args': args, 'data': df,
      'text': $('#textbox').val()
    }), (pl) => {
      pl = new Template(pl)
      templates.push(pl)
      renderPreview(null)
    }
  )
}

function renderPreview(fh) {
  // Render the preview of all current templates on the front page.
  if (fh) {
    df = fh.formdata
    args = g1.url.parse(g1.url.parse(window.location.href).hash).searchList
    refreshTemplates()
    return true
  }
  $('#template-preview').template({templates: templates})
  for (let i = 0; i < templates.length; i++) {
    // add the remove listener
    var deleteListener = function () { deleteTemplate(i) }
    $(`#rm-btn-${i}`).on('click', deleteListener)

    // add setting listener
    var settingsListener = function () { triggerTemplateSettings(i) }
    $(`#settings-btn-${i}`).on('click', settingsListener)
  }
}


function refreshTemplate(n) {
  // Refresh the nth template from the backend
  $.getJSON(`${nlg_base}/nuggets/${n}`).done((e) => {
    templates[n] = new Template(e)
    $('#tmpl-setting-preview').html(templates[n].previewHTML())
    renderPreview(null)
  })
}

function refreshTemplates() {
  // Refresh the output of all templates in the current narrative.
  $.getJSON(`${nlg_base}/narratives`).done((e) => {
    for (let i=0; i<e.length;i++) {
      refreshTemplate(i)
    }
  })
}

function deleteTemplate(n) {
  // Delete a template
  templates.splice(n, 1)
  delete currentEventHandlers[`condt-btn-${n}`]
  renderPreview(null)
}

function triggerTemplateSettings(sentid) {
  // Show the template settings modal for a given template.
  currentTemplateIndex = sentid
  editTemplate(currentTemplateIndex)
  $('#template-settings').modal({ 'show': true })
  $('#condition-editor').focus()
}

function editTemplate(n) {
  // Edit and update a template source.
  $.get(`${nlg_base}/nuggetsettings/${n}`).done(
    (e) => {
      $('#tmpllist').html(e)
    }
  )
}


function setInitialConfig() {
  // At page ready, load the latest config for the authenticated user
  // and show it.
  $.get(`${nlg_base}/initconf`).done((e) => {
    refreshTemplates()
  })
}

function checkTemplate() {
  // Render the template found in the template editor box against the df and args.
  // Show traceback if any.
  $.post(`${nlg_base}/render-template`,
    JSON.stringify({
      'args': args, 'data': df,
      'template': [$('#edit-template').val()]
    })
  ).done(updatePreview).fail(showTraceback)
}

function showTraceback(payload) {
  // Show traceback if tornado.Template(tmpl).generate(**kwargs) fails
  let traceback = $($.parseHTML(payload.responseText)).filter('#traceback')[0]
  $('#traceback').html(traceback.innerHTML)
  $('#tb-modal').modal({ 'show': true })
}


function updatePreview(payload) {
  // Update the preview of a template after it has been edited.
  var template = templates[currentTemplateIndex]
  template.rendered_text = payload[0].text
  template.highlight()
  $('#tmpl-setting-preview').html(template.previewHTML())
}

function saveTemplate() {
  // Update the source for a given template.
  templates[currentTemplateIndex].template = $('#edit-template').val()
  templates[currentTemplateIndex].text = $('#tmpl-setting-preview').text()
  templates[currentTemplateIndex].highlight()
  $('#save-template').attr('disabled', true)
  renderPreview(null)
}

function addCondition() {
  // Add a condition to a template, upon which the template would render.
  var condition = $('#condition-editor').val()
  if (condition) {
    var template = templates[currentTemplateIndex]
    template.condition = condition
    template.makeTemplate()
    $('#edit-template').val(template.template)
  }

}

function addName() {
  // Add an optional name to a template.
  let name = $('#tmpl-name-editor').val()
  if (name) {
    templates[currentTemplateIndex].name = name
  }
}

function getNarrativeEmbedCode() {
  // Generate embed code for this narrative.
  let nlg_path = g1.url.parse(window.location.href).pathname
  let html = `
    <div id="narrative-result"></div>
    <script>
      $('.formhandler').on('load',
        (e) => {
          $.post("${nlg_path}/render-live-template",
            JSON.stringify({
              data: e.formdata,
              nrid: "${narrative_name}", style: true
            }), (f) => $("#narrative-result").html(f)
          )
        }
      )
    </script>
    `
  return html
}

function shareNarrative() {
  // Launch the "Share" modal.
  if (saveConfig()) {
    copyToClipboard(getNarrativeEmbedCode())
  }
}

function copyToClipboard(text) {
  // insert `text` in a temporary element and copy it to clipboard
  var tempTextArea = $('<textarea>')
  $('body').append(tempTextArea)
  tempTextArea.val(text).select()
  document.execCommand('copy')
  tempTextArea.remove()
}

function findAppliedInflections(tkobj) {
  // Find the inflections applied on a given token.
  var applied_inflections = new Set()
  if (tkobj.inflections) {
    for (let i = 0; i < tkobj.inflections.length; i++) {
      applied_inflections.add(tkobj.inflections[i].fe_name)
    }
  }
  return applied_inflections
}
