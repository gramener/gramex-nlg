t_templatize = function (x) {return `{{ ${x} }}`}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

function ignoreTokenTemplate(token) {
    // Ignore all templating applied to a token and revert the template to use
    // the literal token.
    var template = templates[currentEditIndex]
    var enabled_tmpl = getEnabledTemplate(template.tokenmap[token])
    var escaped_tmpl = escapeRegExp(enabled_tmpl.tmpl)
    var expr = `\\{\\{\\ [^\\{\\}]*${escaped_tmpl}[^\\{\\}]*\\ \\}\\}`
    var pattern = new RegExp(expr)
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
    // Opposite of `ignoreTokenTemplate`
    // Apply all templatization to the template and find it.
    var template = templates[currentEditIndex]
    var enabled_tmpl = getEnabledTemplate(template.tokenmap[token])
    var tmplstr = enabled_tmpl.tmpl
    if (token in template.inflections) {
        var infls = template.inflections[token]
        for (let i = 0; i < infls.length; i++ ) {
            tmplstr = makeInflString(tmplstr, infls[i])
        }
    }
    var pattern = new RegExp(token)
    template.template = template.template.replace(pattern, t_templatize(tmplstr))

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
//         url: "set_nlg_gramopt",
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
    var tmplstr = tmpl
    var infl_source = infl.source
    if (infl_source == "str") {
        tmplstr = tmplstr + `.${infl.func_name}()`
    }
    else { tmplstr = `${infl.source}.${infl.func_name}(${tmplstr})` }
    return tmplstr
}

function addFHArgsSetter(sent, fh_args) {
    var setterLine = `{% set fh_args = ${JSON.stringify(fh_args)} %}\n`
    setterLine += `{% set df = U.grmfilter(orgdf, fh_args.copy()) %}\n`
    return setterLine + sent

}

function makeTemplate(searchResult) {
    // make a template from the current searchResult object
    var sent = searchResult.text
    var inflections = searchResult.inflections
    for (let [token, tmpls] of Object.entries(searchResult.tokenmap)) {
        var enabled_tmpl = getEnabledTemplate(searchResult.tokenmap[token])
        var tmplstr = enabled_tmpl.tmpl
        if (token in inflections) {
            tk_infl = inflections[token]
            for (var i = 0; i < tk_infl.length; i ++ ) {
                tmplstr = makeInflString(tmplstr, tk_infl[i])
            }
        }
        sent = sent.replace(token, t_templatize(tmplstr))
    }
    if (searchResult.condition) {
        sent = `{% if ${searchResult.condition} %}\n\t` + sent + "\n{% end %}"
    }
    if (searchResult.setFHArgs) {
        sent = addFHArgsSetter(sent, searchResult.fh_args)
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

function downloadConfig() {
    url = "config-download?config=" + encodeURIComponent(JSON.stringify(templates))
    $.ajax({
        url: url,
        responseType: 'blob',
        type: "GET",
        headers: {'X-CSRFToken': false},
        success: function() { window.location = url }
    })
}

function uploadConfig(e) {
    var reader = new FileReader()
    reader.onload = function () {
        templates = JSON.parse(reader.result)
        renderPreview(null)
        }
    var elem = document.getElementById('config-upload')
    reader.readAsText(elem.files[0])
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
    var condition = document.getElementById('condition-editor').value
    if (condition) {
        var template = templates[currentEditIndex]
        template.condition = condition
        makeTemplate(template)
        document.getElementById('edit-template').value = template.template
    }
    
}

function changeFHSetter(event) {
    template = templates[currentEditIndex]
    template.setFHArgs = document.getElementById('fh-arg-setter').checked
    makeTemplate(template)
    document.getElementById('edit-template').value = template.template
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
    else {
        document.getElementById("condition-editor").value = ""
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

function findAppliedInflections(token, inflections) {
    var applied_inflections = new Set()
    if (token in inflections) {
        tk_infl = inflections[token]
        for (let i = 0; i < tk_infl.length; i ++ ) {
            applied_inflections.add(tk_infl[i].fe_name)
        }
    }
    return applied_inflections
}

function makeGrammarOptionsSelector(token, templateIndex) {
    var html = `<select id="gramopt-select-${templateIndex}-${token}" class="selectpicker show-tick" multiple>`
    var inflections = templates[templateIndex].inflections
    var appliedInfls = findAppliedInflections(token, inflections)
    for (let [fe_name, infl_obj] of Object.entries(grammarOptions)) {
        // check if this inflection is already applied
        if (appliedInfls.has(fe_name)) {
            var selected = "selected"
        }
        else { var selected = "" }
        html += `<option ${selected}>${fe_name}</option>`
    }
    return html + '</select>'
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
        var grop_html = makeGrammarOptionsSelector(token, n)
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

        // add grammar options listeners
        var gramOptSelect = document.getElementById(`gramopt-select-${n}-${token}`)
        gramOptSelect.addEventListener('change', function(e) { changeGrammarOption(token) })

        // add variable assignment listener
        var assignBtn = document.getElementById(`assignvar-${n}-${token}`)
        assignBtn.addEventListener('click', function(e) { assignToVariable(token) })

        // Add remove listener
        var rmtokenbtn = document.getElementById(`rmtoken-${n}-${token}`)
        rmtokenbtn.addEventListener("click", function (e) { ignoreTokenTemplate(token) })
    }
}

function changeGrammarOption(token) {
    // remove all currently applied inflections on the token
    delete templates[currentEditIndex].inflections[token]

    // add the currently selected inflections
    var selected = document.getElementById(`gramopt-select-${currentEditIndex}-${token}`).selectedOptions
    var inflections = Array.from(selected).map(x => x.value)
    var newInflections = [];
    for (i = 0; i < inflections.length; i ++ ) {
        let infl = {}
        let fe_name = inflections[i]
        infl["fe_name"] = fe_name
        infl["source"] = grammarOptions[fe_name]['source']
        infl["func_name"] = grammarOptions[fe_name]['func_name']
        newInflections.push(infl)
    }
    templates[currentEditIndex].inflections[token] = newInflections
    makeTemplate(templates[currentEditIndex])
    document.getElementById('edit-template').value = templates[currentEditIndex].template
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
