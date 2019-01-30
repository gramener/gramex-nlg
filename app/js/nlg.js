t_templatize = function (x) {return `{{ ${x} }}`}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

function ignoreTokenTemplate(token) {
    var template = templates[currentEditIndex]
    var enabled_tmpl = getEnabledTemplate(template.tokenmap[token])
    var escaped_tmpl = escapeRegExp(t_templatize(enabled_tmpl.tmpl))
    var pattern = new RegExp(escaped_tmpl)
    template.template = template.template.replace(pattern, token)
    
    // set editor to current template
    document.getElementById('edit-template').value = template.template

    // change the button to add
    btn = document.getElementById(`rmtoken-${currentEditIndex}-${token}`)
    btn.setAttribute("class", "btn btn-success round")
    btn.setAttribute("title", "Add Token")
    btn.innerHTML = '<i class="fa fa-plus-circle">'
    
    // change the listener to adder
    btn.addEventListener("click", function (e) { addTokenTemplate(token) })
    // btn.click = function (e) { console.log('This is now an adder') }
}

function addTokenTemplate(token) {
    var template = templates[currentEditIndex]
    var enabled_tmpl = getEnabledTemplate(template.tokenmap[token])
    var pattern = new RegExp(token)
    template.template = template.template.replace(pattern, t_templatize(enabled_tmpl.tmpl))

    // set editor to current template
    document.getElementById('edit-template').value = template.template

    // change the button to remove
    btn = document.getElementById(`rmtoken-${currentEditIndex}-${token}`)
    btn.setAttribute("class", "btn btn-danger round")
    btn.setAttribute("title", "Ignore Token")
    btn.innerHTML = '<i class="fa fa-times-circle">'
    
    // change the listener to adder
    btn.addEventListener("click", function (e) { ignoreTokenTemplate(token) })
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

// function makeContextMenuHTML(payload) {
//     var elem = document.getElementById("contextmenu");
//     for (let i = 0; i < payload.length; i++) {
//         var melem = document.createElement('menuitem');
//         melem.label = payload[i];
//         var mylistener = function () { wrapSelection(payload[i]) };
//         melem.addEventListener('click', mylistener);
//         elem.appendChild(melem);
//     }

//     // add Native JS listeners
//     var melem = document.createElement('menuitem');
//     melem.label = "Ignore"
//     melem.addEventListener('click', ignoreTemplateSection)
//     elem.appendChild(melem)

//     var melem = document.createElement('menuitem');
//     melem.label = "Assign to Variable"
//     melem.addEventListener('click', assignToVariable)
//     elem.appendChild(melem)
// }


function getCurrentTokenTemplate(editIndex, token) {
    // get the template currently assigned to the given token
    var template = templates[editIndex]
    var enabled_tmpl = getEnabledTemplate(template.tokenmap[token])
    if (token in template.inflections) {
        var infl = template.inflections[token]
        var inflstring = makeInflString(enabled_tmpl.tmpl, infl)
        return inflstring
    }
    return enabled_tmpl.tmpl
}


function assignToVariable(token) {
    var varname = prompt('Enter variable name:');
    if (varname) {
        var currentTmpl = getCurrentTokenTemplate(currentEditIndex, token)
        var assignmentStr = `{% set ${varname} = ${currentTmpl} %}`
        var pattern = new RegExp(escapeRegExp(t_templatize(currentTmpl)))
        var template = templates[currentEditIndex].template
        var newTemplate = template.replace(pattern, t_templatize(varname))
        templates[currentEditIndex].template = assignmentStr + '\n' + newTemplate
        document.getElementById('edit-template').value = templates[currentEditIndex].template
    }
}

// function setContextMenu() {
//     $.ajax({
//         type: "GET",
//         url: "ctxmenu",
//         success: makeContextMenuHTML
//     })
// }

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


function makeInflString(tmpl, infl) {
    tmplstr = tmpl
    for (let [pymod, funcname] of Object.entries(infl)) {
        if (pymod == "str") {
            funcname = funcname
            tmplstr = tmplstr + '.' + funcname + '()'
        }
        else {
            if (funcname.length > 1) {
                [func, funcargs] = funcname
                tmplstr = `${pymod}.${func}(${tmplstr}, ${funcargs})`
            }
            else {
                func = funcname
                tmplstr = `${pymod}.${func}(${tmplstr})`
            }
        }
    }
    return tmplstr
}


function makeTemplate(searchResult) {
    sent = searchResult.text
    inflections = searchResult.inflections
    for (let [token, tmpls] of Object.entries(searchResult.tokenmap)) {
        for (var i=0; i < tmpls.length; i ++ ) {
            tmpl = tmpls[i]
            if (tmpl.enabled) {
                tmplstr = tmpl.tmpl
                if (token in inflections) {
                    tk_infl = inflections[token]
                    tmplstr = makeInflString(tmplstr, tk_infl)
                }
                sent = sent.replace(token, `{{ ${tmplstr} }}`)
            }
        }
    }
    searchResult.template = sent
}


function highlightTemplate(payload) {
    highlighted = payload.text
    for (let [token, tmpls] of Object.entries(payload.tokenmap)) {
        for (let i = 0; i < tmpls.length; i++ ) {
            tmpl = tmpls[i]
            if (tmpl.enabled) {
                highlighted = highlighted.replace(token,
                    `<span style=\"background-color:#c8f442\">
                        ${token}
                    </span>`);
            }
        }
    }
    payload.previewHTML = highlighted
}

function gramexTemplatize(payload) {
    payload = payload[0]
    makeTemplate(payload)
    highlightTemplate(payload)
    templates.push(payload)
    renderPreview(null)
    // registerTemplateOptions(payload)
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
        success: function() { window.location = url }
    })
}


function getRmButton(n) {
    // Get HTML for the delete template button.
    return `
     <button id="rm-btn-${n}" title="Remove" type="button" class="btn btn-primary">
        <i class="fa fa-trash"></i>
     </button>
     `
}

function getSettingsBtn(n) {
    return `
    <button id="settings-btn-${n}" title="Settings" type="button" class="btn btn-primary">
        <i class="fa fa-wrench"></i>
    </button>
    `
}

function addCondition(event) {
    // Propmt for adding a condition to a template.
    var condition = document.getElementById('condition-editor').value
    if (condition) {
        templates[currentEditIndex].condition = condition
        var currentTemplate = templates[currentEditIndex].template
        var newTemplate = `{% if ${condition} %}\n\t` + currentTemplate + '\n{% end %}'
        templates[currentEditIndex].template = newTemplate
        document.getElementById('edit-template').value = newTemplate
    }
    
}

function editTemplate(n) {
    // Set the template to be edited into the template editor box.
    currentEditIndex = n;
    document.getElementById("edit-template").value = templates[n].template
    document.getElementById("tmpl-setting-preview").textContent = templates[n].text
    currentCondition = templates[n].condition
    if (currentCondition) {
        document.getElementById("condition-editor").value = currentCondition
    }
    makeSettingsTable(n)
}

function getEnabledTemplate(tmpl_list) {
    for (let i = 0; i < tmpl_list.length; i ++ ) {
        tmpl = tmpl_list[i]
        if (tmpl.enabled) {
            return tmpl
        }
    }
}

function makeSearchResultsDropdown(token, tmpl_list) {
    var dropdown_id = `srdd-${currentEditIndex}-${token}`
    var default_tmpl = getEnabledTemplate(tmpl_list)
    var html = `
    <div style="font-family:monospace">
        <select class="selectpicker" id="${dropdown_id}">
            <option selected>
                ${default_tmpl.tmpl}
            </option>`
    for (let i = 0; i < tmpl_list.length; i ++ ) {
        let tmpl = tmpl_list[i]
        if (!(tmpl.enabled)) {
            html += `<div style="font-family:monospace">
                        <option>${tmpl.tmpl}</option>
                     </div>`
        }
    }
    // add dd option change listeners here.
    return html + "</select></div>"
}

function makeGrammarOptionsSelector(token) {
    var dropdown_id = `godd-${currentEditIndex}-${token}`
    var html = `
    <select class="select-multiple" multiple id="${dropdown_id}">
    `
    for (let i = 0; i < grammarOptions.length; i++ ) {
        html += `<option>${grammarOptions[i]}</option>`
    }
    return html + "</select>"
}

function makeSettingsTable(n) {
    // make the HTML table for the nth template.
    var tokenmap = templates[n].tokenmap
    var html = ''
    for (let [token, tmpllist] of Object.entries(tokenmap)) {
        html += `<tr><th scope="row" class="align-middle">${token}</th>`

        if (tmpllist.length > 1) {
            dd_html = makeSearchResultsDropdown(token, tmpllist)
            html += `<td>${dd_html}</td>`
        } else {
            html += `<td class="align-middle" style="font-family:monospace">${tmpllist[0].tmpl}</td>`
        }

        // grammar dropdown
        var grop_html = makeGrammarOptionsSelector(token)
        html += `<td class="align-middle">${grop_html}</td>`

        // add button to assign to variable
        html += `<td class="align-middle">
            <button id="assignvar-${n}-${token}" title="Assign to variable" class="btn btn-success round">
            <i class="fa fa-plus-circle">
        </td>`

        // remover dropdown
        html += `<td class="align-middle">
                 <button id="rmtoken-${n}-${token}" title="Ignore token" class="btn btn-danger round">
                    <i class="fa fa-times-circle">
                 </button></td></tr>`
    }
    document.getElementById('table-body').innerHTML = html
    
    for (let [token, tmpllist] of Object.entries(tokenmap)) {
        // add search result dropdown listeners
        if (tmpllist.length > 1) {
            let dd_id = `srdd-${n}-${token}`
            document.getElementById(dd_id).onchange = function (e) { changeTokenTemplate(token) }
        }
        // add variable assignment listener
        var assignBtn = document.getElementById(`assignvar-${n}-${token}`)
        assignBtn.addEventListener('click', function(e) { assignToVariable(token) })
        // Add remove listener
        var rmtokenbtn = document.getElementById(`rmtoken-${n}-${token}`)
        rmtokenbtn.addEventListener("click", function (e) { ignoreTokenTemplate(token) })
    }
}

function changeTokenTemplate(token) {
    var dd_id = `srdd-${currentEditIndex}-${token}`
    var newTmpl = document.getElementById(dd_id).value
    var tmpllist = templates[currentEditIndex].tokenmap[token]
    for (let i = 0; i < tmpllist.length; i ++ ) {
        tmplobj = tmpllist[i]
        if (tmplobj.tmpl == newTmpl) {
            tmplobj.enabled = true
        }
        else { tmplobj.enabled = false }
    }
    reassignTokenTemplates()
    document.getElementById('edit-template').value = templates[currentEditIndex].template

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
    document.getElementById("tmpl-setting-preview").textContent = payload
}

function saveTemplate() {
    // Save the template found in the template editor box at `currentEditIndex`.
    var tbox = document.getElementById("edit-template");
    var pbox = document.getElementById("tmpl-setting-preview");
    templates[currentEditIndex].template = tbox.value;
    templates[currentEditIndex].previewHTML = pbox.textContent;
    renderPreview(null);
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

function changeTemplateBtn(event) {
    tkmap = templates[currentEditIndex].tokenmap
    for (let [token, tmpllist] of Object.entries(tkmap)) {
        for (let index = 0; index < tmpllist.length; index++) {
            tmpl = tmpllist[index]
            tmpl.enabled = false
            rb = document.getElementById(`rb-${token}-${index}`)
            if (rb.checked) {
                tmpl.enabled = true
            }
        }
    }
    reassignTokenTemplates()
}

function reassignTokenTemplates() {
    for (let index = 0; index < templates.length; index++) {
        makeTemplate(templates[index])
    }
}

function triggerTemplateSettings(sentid) {
    currentEditIndex = sentid
    editTemplate(currentEditIndex)
    // makeTemplateSettingsHTML(currentEditIndex)
    $('#template-settings').modal({'show': true})
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
        innerHTML += getRmButton(i) // + getConditionBtn(i) + getEditTemplateBtn(i)
            + getSettingsBtn(i) + "\t" + templates[i].previewHTML + "</br>";
    }
    innerHTML += "</p>"
    document.getElementById("template-preview").innerHTML = innerHTML;

    // add listeners to buttons
    for (let i = 0; i < templates.length; i++) {

        // add the remove listener
        var btn = document.getElementById(`rm-btn-${i}`)
        var deleteListener = function () { deleteTemplate(i) };
        btn.addEventListener("click", deleteListener);

        // add setting listener
        var btn = document.getElementById(`settings-btn-${i}`)
        var settingsListener = function () { triggerTemplateSettings(i) };
        btn.addEventListener("click", settingsListener);

    }
}
