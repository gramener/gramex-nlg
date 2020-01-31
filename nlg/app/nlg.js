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
  if (clickedVar || (clickedVar === 0)) {
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
      $.get(`${nlg_base}/newvariable/${currentTemplateIndex}/${textSel.join(',')}`).done(
        (e) => {
          $('#variable-settings').html(e)
        }
      )
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
  $('#template-preview').template({n_templates: templates.length})
  for (let i = 0; i < templates.length; i++) {
    // add the remove listener
    var deleteListener = function () { deleteTemplate(i) }
    $(`#rm-btn-${i}`).on('click', deleteListener)

    // add setting listener
    var settingsListener = function () { triggerTemplateSettings(i) }
    $(`#settings-btn-${i}`).on('click', settingsListener)

    // Add the preview
    $.get(`${nlg_base}/render-template/${i}`).done(
      (e) => {$(`#preview-${i}`).text(e)}
    )
  }
  $.get(`${nlg_base}/renderall`).done(
    (e) => {$(`#previewspan`).text(e)}
  )
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
  templates = []
  $.getJSON(`${nlg_base}/narratives`).done((e) => {
    for (let i=0; i<e.length;i++) {
      refreshTemplate(i)
    }
  })
}

function deleteTemplate(n) {
  // Delete a template
  $.getJSON(`${nlg_base}/nuggets/${n}?delete`).done((e) => {
    templates = []
    for (i=0; i<e.length; i++) {
      templates[i] = new Template(e[i])
      $('#tmpl-setting-preview').html(templates[i].previewHTML())
    }
    renderPreview(null)
  })
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
          $.post("${nlg_path}render-live-template",
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

function generateEmbedCode() {
  let url = $('#embedTargetURL').val()
  $('#embedCodeText').text(url)
}

function saveNarrative(name) {
  narrative_name = name
  $.get(`${nlg_base}/saveNarrative/${name}`)
}
