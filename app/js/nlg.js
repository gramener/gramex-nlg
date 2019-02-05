class Template {
    constructor(text, tokenmap, inflections, fh_args, condition ='', setFHArgs = false) {
        this.text = text
        this.tokenmap = {}
        this.inflections = inflections
        for (let [token, tokenlist] of Object.entries(tokenmap)) {
            this.tokenmap[token] = new Token(this, token, tokenlist, this.inflections[token])
        }
        this.fh_args = fh_args
        this.setFHArgs = setFHArgs
        this.condition = condition
        this.template = ""
    }

    makeTemplate() {
        var sent = this.text
        for (let [tk, tokenobj] of Object.entries(this.tokenmap)) {
            sent = sent.replace(tk, tokenobj.makeTemplate())
            if (tokenobj.varname) {
                var pattern = new RegExp(escapeRegExp(tokenobj.template))
                sent = sent.replace(pattern, t_templatize(tokenobj.varname))
                sent = `{% set ${tokenobj.varname} = ${tokenobj.makeTemplate()} %}\n\t` + sent
            }
        }
        if (this.condition) {
            sent = `{% if ${this.condition} %}\n\t` + sent + "\n{% end %}"
        }
        if (this.setFHArgs) {
            sent = addFHArgsSetter(sent, this.fh_args)
        }
        this.template = sent
        this.highlight()
        document.getElementById('edit-template').value = this.template
    }

    highlight() {
        var highlighted = this.text
        for (let [tk, tkobj] of Object.entries(this.tokenmap)) {
            highlighted = highlighted.replace(tk,
                `<span style=\"background-color:#c8f442\">
                    ${tk}
                </span>`);
        }
        this.previewHTML = highlighted
    }

    assignToVariable(token) {
        var token = this.tokenmap[token]
        if (!(token.varname)) {
            var varname = prompt('Enter variable name:')
            if (varname) {
                token.varname = varname
            }
            this.makeTemplate()
       }
    }

    ignoreTokenTemplate(token) {
        var enabled = token.enabledTemplate
        var escaped = escapeRegExp(enabled.tmpl)
        var expr = `\\{\\{\\ [^\\{\\}]*${escaped}[^\\{\\}]*\\ \\}\\}`
        var pattern = new RegExp(expr)
        this.template = this.template.replace(pattern, token.text)

        // UI
        document.getElementById('edit-template').value = this.template
        var btn = document.getElementById(`rmtoken-${currentEditIndex}-${token.text}`)
        btn.setAttribute("class", "btn btn-success round")
        btn.setAttribute("title", "Add Token")
        btn.innerHTML = '<i class="fa fa-plus-circle">'
        
        // change the listener to adder
        var parent = this
        btn.addEventListener("click", function (e) { parent.addTokenTemplate(token) })
    }
    
    addTokenTemplate(token) {
        var enabled_tmpl = token.enabledTemplate
        var tmplstr = enabled_tmpl.tmpl
        if (token.inflections) {
            for (let i = 0; i < token.inflections.length; i++ ) {
                tmplstr = makeInflString(tmplstr, token.inflections[i])
            }
        }
        var pattern = new RegExp(token.text)
        this.template = this.template.replace(pattern, t_templatize(tmplstr))

        // UI
        document.getElementById('edit-template').value = this.template
        var btn = document.getElementById(`rmtoken-${currentEditIndex}-${token.text}`)
        btn.setAttribute("class", "btn btn-danger round")
        btn.setAttribute("title", "Ignore Token")
        btn.innerHTML = '<i class="fa fa-times-circle">'
        
        // change the listener to remover
        var parent = this
        btn.addEventListener("click", function (e) { parent.ignoreTokenTemplate(token) })
    }

    

    get condition() {
        return this._condition
    }

    set condition(condt) {
        this._condition = condt
    }

    get fh_args() {
        return this._fh_args
    }

    set fh_args(fh_args) {
        this._fh_args = fh_args
    }

    makeSettingsTable() {
        // make the HTML table for the nth template.
        var html = ''
        for (let [token, tkobj] of Object.entries(this.tokenmap)) {
            html += `<tr><th scope="row" class="align-middle">${token}</th>`

            if (tkobj.tokenlist.length > 1) {
                var dd_html = tkobj.makeSearchResultsDropdown()
                html += `<td>${dd_html}</td>`
            } else {
                html += `<td class="align-middle" style="font-family:monospace">${tkobj.tokenlist[0].tmpl}</td>`
            }

            // grammar dropdown
            var grop_html = tkobj.makeGrammarOptionsSelector(currentEditIndex)
            html += `<td class="align-middle">${grop_html}</td>`

            // add button to assign to variable
            html += `<td class="align-middle">
                <button id="assignvar-${currentEditIndex}-${token}" title="Assign to variable" class="btn btn-success round">
                <i class="fa fa-plus-circle">
            </td>`

            // remover dropdown
            html += `<td class="align-middle">
                    <button id="rmtoken-${currentEditIndex}-${token}" title="Ignore token" class="btn btn-danger round">
                        <i class="fa fa-times-circle">
                    </button></td></tr>`
        }
        document.getElementById('table-body').innerHTML = html
        
        for (let [token, tkobj] of Object.entries(this.tokenmap)) {
            // add search result dropdown listeners
            if (tkobj.tokenlist.length > 1) {
                let dd_id = `srdd-${currentEditIndex}-${token}`
                document.getElementById(dd_id).onchange = function (e) { tkobj.changeTokenTemplate() }
            }

            // add grammar options listeners
            var gramOptSelect = document.getElementById(`gramopt-select-${currentEditIndex}-${token}`)
            gramOptSelect.addEventListener('change', function(e) { tkobj.changeGrammarOption() })

            // add variable assignment listener
            var assignBtn = document.getElementById(`assignvar-${currentEditIndex}-${token}`)
            var parent = this
            assignBtn.addEventListener('click', function(e) { parent.assignToVariable(token) })

            // Add remove listener
            var rmtokenbtn = document.getElementById(`rmtoken-${currentEditIndex}-${token}`)
            rmtokenbtn.addEventListener("click", function (e) { parent.ignoreTokenTemplate(tkobj) })
        }
    }
}

class Token {
    constructor(parent, text, tokenlist, inflections, varname = null) {
        this.parent = parent
        this.text = text
        this.tokenlist = tokenlist
        this.inflections = inflections
        this.varname = varname
        this.template = ""
    }

    get varname() {
        return this._varname
    }

    set varname(value) {
        if (value) {
            this._varname = value
            this.template = `{{ ${this._varname} }}`
        }
    }

    makeTemplate() {
        var enabled = this.enabledTemplate
        var tmplstr = enabled.tmpl
        if (this.inflections) {
            for (let i = 0; i < this.inflections.length; i ++ ) {
                tmplstr = makeInflString(tmplstr, this.inflections[i])
            }
        }
        this.template = t_templatize(tmplstr)
        return this.template
    }

    get enabledTemplate() {
        for (let i = 0; i < this.tokenlist.length; i ++ ) {
            if (this.tokenlist[i].enabled) {
                return this.tokenlist[i]
            }
        }
    }

    makeSearchResultsDropdown() {
        var dropdown_id = `srdd-${currentEditIndex}-${this.text}`
        var html = `
            <div style="font-family:monospace">
            <select class="selectpicker" id="${dropdown_id}">
            <option selected>
                ${this.enabledTemplate.tmpl}
            </option>`
        for (let i = 0; i < this.tokenlist.length; i ++ ) {
            let tmpl = this.tokenlist[i]
            if (!(tmpl.enabled)) {
                html += `<div style="font-family:monospace">
                            <option>${tmpl.tmpl}</option>
                        </div>`
            }
        }
        // add dd option change listeners here.
        return html + "</select></div>"
    }

    findAppliedInflections() {
        var applied_inflections = new Set()
        if (this.inflections) {
            for (let i = 0; i < this.inflections.length; i ++ ) {
                applied_inflections.add(this.inflections[i].fe_name)
            }
        }
        return applied_inflections
    }

    makeGrammarOptionsSelector(editIndex) {
        var html = `<select id="gramopt-select-${editIndex}-${this.text}" class="selectpicker show-tick" multiple>`
        var appliedInfls = this.findAppliedInflections()
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

    changeGrammarOption() {
        // remove all currently applied inflections on the token
        this.inflections = []

        // add the currently selected inflections
        var selected = document.getElementById(`gramopt-select-${currentEditIndex}-${this.text}`).selectedOptions
        var inflections = Array.from(selected).map(x => x.value)
        var newInflections = [];
        for (let i = 0; i < inflections.length; i ++ ) {
            let infl = {}
            let fe_name = inflections[i]
            infl["fe_name"] = fe_name
            infl["source"] = grammarOptions[fe_name]['source']
            infl["func_name"] = grammarOptions[fe_name]['func_name']
            newInflections.push(infl)
        }
        this.inflections = newInflections
        this.parent.makeTemplate()
    }

    changeTokenTemplate() {
        var dd_id = `srdd-${currentEditIndex}-${this.text}`
        var newTmpl = document.getElementById(dd_id).value
        for (let i = 0; i < this.tokenlist.length; i ++ ) {
            var tmplobj = this.tokenlist[i]
            if (tmplobj.tmpl == newTmpl) {
                tmplobj.enabled = true
            }
            else { tmplobj.enabled = false }
        }
        this.parent.makeTemplate()
    }
}


function addToNarrative() {
    // pick text from the "Type something" box, templatize, and add to narrative
    $.ajax({
        type: "POST",
        url: "textproc",
        data: { "args": JSON.stringify(args), "data": JSON.stringify(df),
                "text": JSON.stringify([document.getElementById("textbox").value]) },
        success: addToTemplates
    })
}

function addToTemplates(payload) {
    var payload = payload[0]
    var template = new Template(
        payload.text, payload.tokenmap, payload.inflections, payload.fh_args, setFHArgs=payload.setFHArgs)
    template.makeTemplate()
    templates.push(template)
    renderPreview(null)
}

function renderPreview(fh) {
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

function refreshTemplates() {
    var tmpls = templates.map(x => x.template)
    $.ajax({
        type: "POST",
        url: "render-template",
        data: { "args": JSON.stringify(args), "data": JSON.stringify(df),
                "template": JSON.stringify(tmpls) },
        success: function (payload) { updateTemplates(payload, templates) }
    })
}

function updateTemplates(payload) {
    for (let i = 0; i < payload.length; i ++ ) {
        var tmpl = templates[i]
        tmpl.text = payload[i]
        tmpl.highlight()
    }
    renderPreview(null)
}

function deleteTemplate(n) {
    // Delete a template
    templates.splice(n, 1)
    delete currentEventHandlers[`condt-btn-${n}`]
    renderPreview(null);
}

function triggerTemplateSettings(sentid) {
    currentEditIndex = sentid
    editTemplate(currentEditIndex)
    $('#template-settings').modal({'show': true})
}

function editTemplate(n) {
    currentEditIndex = n
    document.getElementById("edit-template").value = templates[n].template
    document.getElementById("tmpl-setting-preview").textContent = templates[n].text
    currentCondition = templates[n].condition
    if (currentCondition) {
        document.getElementById("condition-editor").value = currentCondition
    }
    else {
        document.getElementById("condition-editor").value = ""
    }
    templates[n].makeSettingsTable()
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
        args = null;
        renderPreview(null)
        }
    var elem = document.getElementById('config-upload')
    reader.readAsText(elem.files[0])
}

function checkTemplate() {
    // Render the template found in the template editor box against the df and args.
    renderTemplate([document.getElementById("edit-template").value], editAreaCallback);
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

function editAreaCallback(payload) {
    document.getElementById("tmpl-setting-preview").textContent = payload
}

function saveTemplate() {
    // Save the template found in the template editor box at `currentEditIndex`.
    var tbox = document.getElementById("edit-template");
    var pbox = document.getElementById("tmpl-setting-preview");
    templates[currentEditIndex].template = tbox.value;
    templates[currentEditIndex].text = pbox.textContent;
    templates[currentEditIndex].highlight()
    renderPreview(null);
}

function addCondition(event) {
    var condition = document.getElementById('condition-editor').value
    if (condition) {
        var template = templates[currentEditIndex]
        template.condition = condition
        template.makeTemplate()
        document.getElementById('edit-template').value = template.template
    }
    
}

function changeFHSetter(event) {
    template = templates[currentEditIndex]
    template.setFHArgs = document.getElementById('fh-arg-setter').checked
    template.makeTemplate()
    document.getElementById('edit-template').value = template.template
}

t_templatize = function (x) {return `{{ ${x} }}`}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
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

// Markup buttons
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