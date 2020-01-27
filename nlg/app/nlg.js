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

// function makeGrammarErrorPopover(span, errobj) {
//   // Parse the grammar error from LanguageTool and display it as a popover.
//   var errmsg = errobj.message.replace(/"/g, '\'')
//   return `<span style="background-color:#ed7171" data-toggle="popover" data-trigger="hover"
//     title="${errmsg}"
//     data-placement="top">${span}</span>`
// }

// class Token {
//   // Class to hold a token contained within a template.
//   // In a tornado template, a token is anything enclosed within double braces.
//   constructor(parent, text, tokenlist, inflections, template = '') {
//     this.parent = parent
//     this.text = text
//     this.tokenlist = tokenlist
//     this.inflections = inflections
//     this.template = template
//   }
//
//   toJSON() {
//     return {
//       text: this.text, tokenlist: this.tokenlist, inflections: this.inflections,
//       template: this.template
//     }
//   }
//
//   makeTemplate() {
//     var enabled = this.enabledTemplate
//     var tmplstr = enabled.tmpl
//     if (this.inflections) {
//       for (let i = 0; i < this.inflections.length; i++) {
//         tmplstr = makeInflString(tmplstr, this.inflections[i])
//       }
//     }
//     if (this.varname) {
//       this.template = tmplstr
//     } else { this.template = t_templatize(tmplstr) }
//     return this.template
//   }
//
//   get enabledTemplate() {
//     for (let i = 0; i < this.tokenlist.length; i++) {
//       if (this.tokenlist[i].enabled) {
//         return this.tokenlist[i]
//       }
//     }
//     return undefined
//   }
//
//   changeGrammarOption() {
//     // Change the applied inflections on the token.
//     this.inflections = []
//
//     // add the currently selected inflections
//     var inflections = $(`#gramopt-select-${currentTemplateIndex}-${this.text.replace(/\s/g, '_')}`).val()
//     var newInflections = []
//     for (let i = 0; i < inflections.length; i++) {
//       let infl = {}
//       let fe_name = inflections[i]
//       infl['fe_name'] = inflections[i]
//       infl['source'] = grammarOptions[fe_name]['source']
//       infl['func_name'] = grammarOptions[fe_name]['func_name']
//       newInflections.push(infl)
//     }
//     this.inflections = newInflections
//     this.parent.makeTemplate()
//   }
//
//   changeTokenTemplate() {
//     // Re-generate the template for this token based on applied inflections, etc.
//     var newTmpl = $(`#srdd-${currentTemplateIndex}-${this.text.replace(/\s/g, '_')}`).val()
//     for (let i = 0; i < this.tokenlist.length; i++) {
//       var tmplobj = this.tokenlist[i]
//       if (tmplobj.tmpl == newTmpl) {
//         tmplobj.enabled = true
//       }
//       else { tmplobj.enabled = false }
//     }
//     this.parent.makeTemplate()
//   }
// }


function addToNarrative() {
  // Pick text from the input textarea, templatize, and add to the narrative.
  $.post(
    `${nlg_base}/textproc`,
    JSON.stringify({
      'args': args, 'data': df,
      'text': $('#textbox').val()
    }), (pl) => {
      // var template = new Template(
      //   payload.text, payload.tokenmap, payload.inflections, payload.fh_args)
      // template.makeTemplate()
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
  $.post(`${nlg_base}/render-template`,
    JSON.stringify({
      'args': args, 'data': df,
      'template': templates.map(x => x.template)
    }), (e) => {
      for (let i = 0; i < e.length; i++) {
        var tmpl = templates[i]
        tmpl.rendered_text = e[i].text
        tmpl.grmerr = e[i].grmerr
        tmpl.highlight()
      }
      renderPreview(null)
    }
  )
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
  // $('#edit-template').val(templates[n].template)
  // $('#tmpl-setting-preview').html(templates[n].previewHTML(true))
  // $('#condition-editor').val(templates[n].condition)
  // $('#tmpl-name-editor').val(templates[n].name)
  // templates[n].makeSettingsTable()
  $.get(`${nlg_base}/nuggetsettings/${n}`).done(
     (e) => {
       $('#tmpllist').html(e)
     }
  )
}


function saveConfig() {
  // Save the current narrative to $GRAMEXDATA/nlg/{{ handler.current_user.email }}/
  var elem = $('#narrative-name-editor')
  if (!(elem.val())) {
    alert('Please name the narrative.')
    elem.focus()
    return false
  } else {
    narrative_name = elem.val()
    $.ajax({
      url: `${nlg_base}/save-config`,
      type: 'POST',
      data: { config: JSON.stringify(templates), name: narrative_name, dataset: dataset_name },
      headers: { 'X-CSRFToken': false },
      success: function () { $('.alert-success').show() },
      error: function(httpObj) {
        if (httpObj.status == 401) {
          alert('Please login to save the narrative.')
        }
      }
    })
  }
  return true
}

function setInitialConfig() {
  // At page ready, load the latest config for the authenticated user
  // and show it.
  $.getJSON(`${nlg_base}/initconf`).done((e) => {
    dataset_name = e.dsid
    narrative_name = e.nrid
    if (e.config) { setConfig(e.config) }
  })
}

function setConfig(configobj) {
  // Set the config for a given (user, narrative_id) pair.
  templates = []
  for (let i = 0; i < configobj.config.length; i++) {
    var tmpl = configobj.config[i]
    var tmplobj = new Template(
      tmpl.source_text, tmpl.tokenmap, tmpl.inflections,
      tmpl._fh_args, tmpl._condition,
      tmpl.template, tmpl.previewHTML(), tmpl.grmerr, tmpl.name)
    templates.push(tmplobj)
  }
  $('#narrative-name-editor').val(configobj.name)
  args = null
  renderPreview(null)
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

/* eslint-disable no-unused-vars */
function t_templatize(x) { return '{{ ' + x + ' }}' }
/* eslint-enable no-unused-vars */

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')  // $& means the whole matched string
}

function makeInflString(tmpl, infl) {
  // Detect chosen inflections for a token and convert them to Tornado templates.
  var tmplstr = tmpl
  var infl_source = infl.source
  if (infl_source == 'str') {
    tmplstr = tmplstr + `.${infl.func_name}()`
  }
  else { tmplstr = `${infl.source}.${infl.func_name}(${tmplstr})` }
  return tmplstr
}

function addFHArgsSetter(sent, fh_args) {
  // Add formhandler arguments or URL filters to the template.
  let setterLine = `{% set fh_args = ${JSON.stringify(fh_args)} %}\n`
  setterLine += '{% set df = U.gfilter(orgdf, fh_args.copy()) %}\n'
  return setterLine + sent
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
