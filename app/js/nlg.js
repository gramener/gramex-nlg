function ignoreTemplateSection(event) {
    var editor = document.getElementById('edit-template')
    var currentText = editor.value;
    var start = editor.selectionStart;
    var end = editor.selectionEnd;
    var selection = currentText.substring(start, end)
    var replacement = deTemplatizeSelection(selection, currentEditIndex)
    if (replacement) {
        editor.value =  currentText.replace(selection, replacement)
    }
}

function deTemplatizeSelection(selection, index) {
    var tkmap = templates[index].tokenmap
    var pandasExpr = selection.replace(/(^{{\ |\ }})/g, "")
    for (let [token, tmpl] of Object.entries(tkmap)) {
        if (pandasExpr == tmpl) {
            return token
        }
    }
    return false
}

function wrapSelection(pyfunc) {
    var editor = document.getElementById('edit-template');
    var currentText = editor.value;
    var start = editor.selectionStart;
    var end = editor.selectionEnd;
    var oldSelection = currentText.substring(start, end);
    var newSelection = `{{ ${pyfunc}('${oldSelection}') }}`;
    editor.value = currentText.replace(oldSelection, newSelection)
}

function makeContextMenuHTML(payload) {
    var elem = document.getElementById("contextmenu");
    for (let i = 0; i < payload.length; i++) {
        var melem = document.createElement('menuitem');
        melem.label = payload[i];
        var mylistener = function () { wrapSelection(payload[i]) };
        melem.addEventListener('click', mylistener);
        elem.appendChild(melem);
    }

    // add Native JS listeners
    var melem = document.createElement('menuitem');
    melem.label = "Ignore"
    melem.addEventListener('click', ignoreTemplateSection)
    elem.appendChild(melem)

    var melem = document.createElement('menuitem');
    melem.label = "Assign to Variable"
    melem.addEventListener('click', assignToVariable)
    elem.appendChild(melem)
}

function assignToVariable(event) {
    var editor = document.getElementById('edit-template');
    var currentText = editor.value;
    var start = editor.selectionStart;
    var end = editor.selectionEnd;
    var selection = currentText.substring(start, end)
    var varString = selection.replace(/(^{{\ |\ }}$)/g, '')
    var assignmentStr = `{% set x = ${varString} %}`
    editor.value = assignmentStr + '\n' + currentText
}

function setContextMenu() {
    $.ajax({
        type: "GET",
        url: "ctxmenu",
        success: makeContextMenuHTML
    })
}

function addToNarrative() {
    // Add a template to the list of templates.
    $.ajax({
        type: "POST",
        url: "textproc",
        data: { "args": JSON.stringify(args), "data": JSON.stringify(df),
                "text": JSON.stringify([document.getElementById("textbox").value]) },
        success: gramexTemplatize
    })
}

function makeTemplate(searchResult) {
    sent = searchResult.text
    for (let [token, tmpls] of Object.entries(searchResult.tokenmap)) {
        for (var i=0; i < tmpls.length; i ++ ) {
            tmpl = tmpls[i]
            if (tmpl.enabled) {
                sent = sent.replace(token, `{{ ${tmpl.tmpl} }}`)
            }
        }
    }
    searchResult.template = sent
}


function highlightTemplate(payload) {
    highlighted = payload.template
    for (let [token, tmpls] of Object.entries(payload.tokenmap)) {
        if (tmpls.length == 1) {
            span_id = `${templates.length}-${token}-0`
            tmpl = tmpls[0]
            highlighted = highlighted.replace(`{{ ${tmpl.tmpl} }}`,
                `<span id="${span_id}" style=\"background-color:#c8f442\" title="${tmpl.tmpl}">
                    ${token}
                </span>`);
        }
        else {
            for (var i = 0; i < tmpls.length; i++ ) {
                span_id = `${templates.length}-${token}-${i}`
                tmpl = tmpls[i]
                if (tmpl.enabled) {
                    highlighted = highlighted.replace(`{{ ${tmpl.tmpl} }}`,
                        `<span id="${span_id}" style=\"background-color:#c8f442\" title="Click for options">
                            ${token}
                        </span>`);
                }
            }
        }
    }
    payload.previewHTML = highlighted
}

function getTemplateBySpanId(span_id) {
    let re = /(\d+)\-(.+)\-(\d+)/gm
    let [_, sent_id, token, token_tmpl_id] = re.exec(span_id)
    token_tmpls = templates[sent_id].tokenmap[token]
    makeTemplateSelectorHTML(token_tmpls)
}

function makeTemplateSelectorHTML(token_tmpls) {
    html = ''
    for (let i = 0; i < token_tmpls.length; i ++ ) {
        tmpl = token_tmpls[i]
        if (tmpl.enabled) {
            var check = "checked"
        } else { var check = "" }
        html += `
        <div class="radio">
        <label style="font-family:monospace">
            <input id="token-tmpl-${i}" type="radio" name="optradio" ${check}>${tmpl.tmpl}</label>
        </div>`
    }
    document.getElementById("tmplradiolist").innerHTML = html
}


function editTokenTemplate(event, span_id) {
    currentSpanId = span_id
    getTemplateBySpanId(span_id)
    $('#template-select').modal({'show': true})
}


function registerTemplateOptions(payload) {
    for (let [token, tmpls] of Object.entries(payload.tokenmap)) {
        for (let i = 0; i < tmpls.length; i ++ ) {
            currentTemplate = templates.length - 1
            let span_id = `${currentTemplate}-${token}-${i}`
            span = document.getElementById(span_id)
            if (span) {
                span.addEventListener('click', function (event) {editTokenTemplate(event, span_id)})
            }
        }
    }
}


function changeTemplateBtn(event) {
    let re = /(\d+)\-(.+)\-(\d+)/gm
    let [_, sent_id, token, tid] = re.exec(currentSpanId)
    template = templates[sent_id]
    tokenlist = template.tokenmap[token]
    for (let index = 0; index < tokenlist.length; index++) {
        token_tmpl_id = `token-tmpl-${index}`
        elem = document.getElementById(token_tmpl_id)
        if (elem.checked) {
            for (let i = 0; i < tokenlist.length; i++) {
                tokenlist[i].enabled = false
            }
            template.tokenmap[token] = tokenlist
            template.tokenmap[token][index].enabled = true
            reassignTokenTemplates();
            return true
        }
    }
}

// Depending on which template ID is active in all templates,
// update them
function reassignTokenTemplates() {
    for (let index = 0; index < templates.length; index++) {
        template = templates[index]
        sent = template.text
        for (let [token, tmpls] of Object.entries(template.tokenmap)) {
            for (var i=0; i < tmpls.length; i ++ ) {
                tmpl = tmpls[i]
                if (tmpl.enabled) {
                    sent = sent.replace(token, `{{ ${tmpl.tmpl} }}`)
                }
            }
        }
        template.template = sent
    }
}


function gramexTemplatize(payload) {
    payload = payload[0]
    makeTemplate(payload)
    highlightTemplate(payload)
    templates.push(payload)
    renderPreview(null)
    registerTemplateOptions(payload)
    document.getElementById("textbox").value = "";
}

function saveBlob(blob, fileName) {
    // Helper to save / download files.
    var a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = fileName.replace(/(^_|_$)/g, '');
    // click working with firefox & chrome: https://stackoverflow.com/a/22469115/
    a.dispatchEvent(new MouseEvent('click', {
        'view': window,
        'bubbles': true,
        'cancelable': false
    }));
}

function downloadNarrative() {
    // Download the narrative as injected into a Python file.
    currentTemplates = templates.map(x => x.template)
    currentConditions = templates.map(x => x.condition)
    url = "tmpl-download?tmpl="
        + encodeURIComponent(JSON.stringify(currentTemplates))
        + "&condts=" + encodeURIComponent(JSON.stringify(currentConditions))
        + "&args=" + encodeURIComponent(JSON.stringify(args))
    $.ajax({
        url: url,
        responseType: 'blob',
        type: "GET",
        headers: {'X-CSRFToken': false},
        success: function (event) {
            var blob = this.response;
            var contentDispo = this.getResponseHeader('Content-Disposition');
            // https://stackoverflow.com/a/23054920/
            var fileName = contentDispo.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
            saveBlob(blob, fileName);
        }
    })
}


function getConditionBtn(n) {
    // Get HTML for the "Add Condition" button.
    return `<input id="condt-btn-${n}" type="button" value="Add Condition"/>`
}

function getRmButton(n) {
    // Get HTML for the delete template button.
    return `
     <button id="rm-btn-${n}" title="Remove" type="button" class="btn btn-primary">
        <i class="fa fa-trash"></i>
     </button>
     `
}

function getEditTemplateBtn(n) {
    // Get HTML for the edit template button.
    return `
     <button id="edit-btn-${n}" title="Edit" type="button" class="btn btn-primary">
        <i class="fa fa-edit"></i>
     </button>
     `
}


function addCondition(n) {
    // Propmt for adding a condition to a template.
    var expr = prompt('Enter Expression:');
    if (expr) {
        templates[n].condition = expr;
        var btn = document.getElementById(`condt-btn-${n}`);
        btn.value = "Edit Condition";
        btn.removeEventListener("click", currentEventHandlers[`condt-btn-${n}`])
        var newlistner = function () { editCondition(n) };
        btn.addEventListener("click", newlistner);
        currentEventHandlers[`condt-btn-${n}`] = newlistner;
    }
}

function editCondition(n) {
    // Propmt for editing a condition on a template.
    var expr = prompt("Enter Expression:", templates[n].condition);
    if (expr) {
        templates[n].condition = expr
    }
    else if (expr === "") {
        templates[n].condition = "";
        var btn = document.getElementById(`condt-btn-${n}`);
        btn.value = "Add Condition";
        btn.removeEventListener("click", currentEventHandlers[`condt-btn-${n}`])
        var newlistner = function () { addCondition(n) };
        btn.addEventListener("click", newlistner);
        currentEventHandlers[`condt-btn-${n}`] = newlistner;
    }

}

function editTemplate(n) {
    // Set the template to be edited into the template editor box.
    currentEditIndex = n;
    document.getElementById("edit-template").value = templates[n].template;
}

function deleteTemplate(n) {
    // Delete a template
    templates.splice(n, 1)
    delete currentEventHandlers[`condt-btn-${n}`]
    renderPreview(null);
}

function renderTemplate(text, success) {
    // render an arbitrary template and do `success` on success.
    $.ajax({
        type: "POST",
        url: "render-template",
        data: {
            "args": JSON.stringify(args), "data": JSON.stringify(df),
            "template": JSON.stringify(text)
        },
        success: success
    })
}

function checkTemplate() {
    // Render the template found in the template editor box against the df and args.
    renderTemplate([document.getElementById("edit-template").value], editAreaCallback);
}

function editAreaCallback(payload) {
    document.getElementById("edit-preview").innerHTML = payload;
}

function saveTemplate() {
    // Save the template found in the template editor box at `currentEditIndex`.
    var tbox = document.getElementById("edit-template");
    var pbox = document.getElementById("edit-preview");
    templates[currentEditIndex].template = tbox.value;
    templates[currentEditIndex].previewHTML = pbox.innerHTML;
    renderPreview(null);
    tbox.value = "";
    currentEditIndex = null;
}

function refreshTemplates() {
    // get all current templates, run against current formhandler,
    // and repopulate the templates
    if (templates.length > 0) {
        currentTemplates = templates.map(x => x.template)
        $.ajax({
            type: "POST",
            url: "render-template",
            data: { "args": JSON.stringify(args), "data": JSON.stringify(df),
                    "template": JSON.stringify(currentTemplates) },
            success: function (payload) { updateTemplates(payload, templates) }
        })
    }
}

function updateTemplates(payload) {
    for (let i = 0; i < payload.length; i ++ ) {
        var tmpl = templates[i]
        tmpl.text = payload[i]
        tmpl.previewHTML = payload[i]
    }
    renderPreview(null)
}

function renderPreview(fh) {
    // Render the list of templates and their renditions
    if (fh) {
        df = fh.formdata
        args = g1.url.parse(g1.url.parse(window.location.href).hash).searchList
        refreshTemplates()
        return true
    }
    
    var innerHTML = "<p>\n";
    for (var i = 0; i < templates.length; i++) {
        innerHTML += getRmButton(i) + getEditTemplateBtn(i) + getConditionBtn(i)
            + "\t" + templates[i].previewHTML + "</br>";
    }
    innerHTML += "</p>"
    document.getElementById("template-preview").innerHTML = innerHTML;

    // add listeners to buttons
    for (let i = 0; i < templates.length; i++) {
        var btnkey = `condt-btn-${i}`
        var btn = document.getElementById(btnkey)
        // check if condition already exists
        if ((!(i in templates)) || (templates[i].condition === "")) {
            var listener = function () { addCondition(i) }
        }
        else {
            var listener = function () { editCondition(i) }
        }
        // remove old listeners if any
        if (btnkey in currentEventHandlers) {
            var oldlistener = currentEventHandlers[btnkey];
            btn.removeEventListener("click", oldlistener);
        }
        btn.addEventListener("click", listener);
        currentEventHandlers[btnkey] = listener;

        // add the edit listener
        var btn = document.getElementById(`edit-btn-${i}`)
        var editListener = function () { editTemplate(i) };
        btn.addEventListener("click", editListener)

        // add the remove listener
        var btn = document.getElementById(`rm-btn-${i}`)
        var deleteListener = function () { deleteTemplate(i) };
        btn.addEventListener("click", deleteListener);
    }
}

// function highlightTemplate(template, tokenmap) {
    // var highlighted = template;
    // for (let [token, tmpl] of Object.entries(tokenmap)) {
        // highlighted = highlighted.replace(`{{ ${tmpl} }}`,
            // `<span style=\"background-color:#c8f442\" title="{{ ${tmpl} }}">${token}</span>`);
    // }
    // return highlighted;
// }