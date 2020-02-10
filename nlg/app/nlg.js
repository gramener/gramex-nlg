/* globals currentTemplateIndex, grammarOptions, templates, args, df, currentEventHandlers, nlg_base, g1 */
/* exported addToNarrative, setInitialConfig, checkTemplate, saveTemplate,
addCondition, addName, shareNarrative, copyToClipboard,
findAppliedInflections, checkSelection */
/* eslint-disable no-global-assign */
var narrative_name, dataset_name
var styleparams = {bold: true, italic: false, underline: false, style: 'para'}

function openDemoPage() {
  if (!(narrative_name)) {
    $('#saveModal').modal({show: true})
  } else {
    let fh_url = encodeURIComponent($('.formhandler').attr('data-src'))
    let url = `${nlg_base}/demoembed?fh_url=${fh_url}&nname=${narrative_name}`
    window.open(url)
  }
}

function activateStyleControl() {
  if (styleparams.bold) {
    $('#boldpreview').addClass('active')
  }
  if (styleparams.italic) {
    $('#italicpreview').addClass('active')
  }
  if (styleparams.underline) {
    $('#ulinepreview').addClass('active')
  }

  if (styleparams.style == 'para') {
    $('#parastyle').prop('checked', true)
  } else {
    $('#liststyle').prop('checked', true)
  }
  renderByStyle()
}

function toggleRenderStyle(e) {
  if (e.currentTarget.id == "parastyle") {
    if ($('#parastyle').prop('checked')) {
      styleparams.style = "para"
    }
  } else if (e.currentTarget.id == "liststyle") {
    if ($('#liststyle').prop('checked')) {
      styleparams.style = "list"
    }
  } else if (e.currentTarget.id == "boldpreview") {
    if ($('#boldpreview').hasClass('active')) {
      styleparams.bold = true
    } else {
      styleparams.bold = false
    }
  } else if (e.currentTarget.id == "italicpreview") {
    if ($('#italicpreview').hasClass('active')) {
      styleparams.italic = true
    } else {
      styleparams.italic = false
    }
  } else if (e.currentTarget.id == "ulinepreview") {
    if ($('#ulinepreview').hasClass('active')) {
      styleparams.underline = true
    } else {
      styleparams.underline = false
    }
  }
  renderByStyle()
}

function renderByStyle() {
  let url = g1.url.parse(`${nlg_base}/renderall`)
  url.update(styleparams)
  $.getJSON(url.toString()).done((e) => {
    $(`#previewspan`).html(e.render)
    styleparams = e.style
  })
}

function makeControlDroppable(elem, ondrop) {
  elem.on('dragover', (e) => {
    e.preventDefault()
    e.stopPropagation()
  })
  elem.on('dragleave', (e) => {
    e.preventDefault()
    e.stopPropagation()
  })
  elem.on('drop', (e) => {
    e.preventDefault()
    e.stopPropagation()
    ondrop(e)
  })
}

function prepDrag(row) {
  row.on('dragstart', (e) => {
    e.dataTransfer = e.originalEvent.dataTransfer
    e.dataTransfer.setData('text', e.target.id)})
}


function findControlRow(elem) {
  if (!(elem.id)) {
    return false
  } else {
    return elem.id.match(/^controlrow-\d+$/)
  }
}

function findDropPosition(y) {
  let rows = _.filter(Object.values($('tr[id^=controlrow]')), findControlRow)
  let bottoms = _.flatMap(rows, (r) => {return r.getBoundingClientRect().bottom})
  for (let i=0; i<bottoms.length; i++) {
    if (y <= bottoms[i]) {
      return i
    }
  }
}

function handleDrop(e) {
  e.preventDefault();
  let rowid = e.originalEvent.dataTransfer.getData('text')
  if (rowid.match(/^controlrow-\d+$/g)) {
    let droppos = findDropPosition(e.originalEvent.clientY)
    if (droppos) {
      let poppos = rowid.replace(/^controlrow-/, "")
      $.get(`${nlg_base}/movenugget/${poppos}/${droppos}`).done(
        refreshTemplates(null)
      )
    }
  }
}

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
  makeControlDroppable($('#controltable'), handleDrop)
  for (let i = 0; i < templates.length; i++) {
    // add the remove listener
    var deleteListener = function () { deleteTemplate(i) }
    $(`#rm-btn-${i}`).on('click', deleteListener)

    // add setting listener
    var settingsListener = function () { triggerTemplateSettings(i) }
    $(`#settings-btn-${i}`).on('click', settingsListener)

    // Add the preview
    $.get(`${nlg_base}/render-template/${i}`).done(
      (e) => {$(`#preview-${i}`).html(e)}
    )
    // prep the row for dragging
    prepDrag($(`#controlrow-${i}`))
  }
  renderByStyle()
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
    if (e.narrative.length > 0) {
      for (let i=0; i<e.narrative.length;i++) {
        refreshTemplate(i)
      }
    } else {
      renderPreview(null)
    }
  })
}

function deleteTemplate(n) {
  // Delete a template
  $.getJSON(`${nlg_base}/nuggets/${n}?delete`).done(refreshTemplates)
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
  $.getJSON(`${nlg_base}/initconf`).done((e) => {
    refreshTemplates()
    Object.assign(styleparams, e.style)
    activateStyleControl()
  })
}

function addName() {
  // Add an optional name to a template.
  let name = $('#tmpl-name-editor').val()
  if (name) {
    templates[currentTemplateIndex].name = name
  }
}


function renderLiveNarrative(divid, nname, selector='.formhandler') {
  let elem = $(selector)
  if (elem.length > 0) {
    elem.on('load', (e) => {
      $.post(
        `${nlg_base}/render-live-template`,
        JSON.stringify({
          data: e.formdata,
          nrid: nname}),
        (f) => {$(divid).html(f)}
      )
    })
  } else {
    let url = g1.url.parse(`${nlg_base}/renderall`)
    url.update(styleparams)
    $.getJSON(url.toString()).done((e) => {
      $(divid).html(e.render)
    })
  }
}

function getNarrativeEmbedCode() {
  // Generate embed code for this narrative.
  let html = `
    <div id="narrative-result"></div>
    <script src="${nlg_base}/nlg.js"></script>
    <script>
      var nlg_base = "${nlg_base}"
      renderLiveNarrative("#narrative-result", "${narrative_name}")
    </script>`
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
