function getSearchArgs() {
    var url = window.location.href;
    return g1.url.parse(url).hash;
}

function setDataArgs(x) {
    df = x.formdata;
    args = getSearchArgs();
}

function addToTemplate() {
    $.ajax({
        type: "POST",
        url: "textproc",
        data: { "args": args, "data": JSON.stringify(df), "text": document.getElementById("textbox").value },
        success: textAreaCallback
    })
}

function saveBlob(blob, fileName) {
    var a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = fileName;
    // click working with firefox & chrome: https://stackoverflow.com/a/22469115/
    a.dispatchEvent(new MouseEvent('click', {
        'view': window,
        'bubbles': true,
        'cancelable': false
    }));
}

function downloadTemplate() {
    var request = new XMLHttpRequest();
    request.open('GET', "/tmpl-download?tmpl="
        + encodeURIComponent(JSON.stringify(nlg_template))
        + "&condts=" + encodeURIComponent(JSON.stringify(conditions))
        + "&args=" + encodeURIComponent(JSON.stringify(getSearchArgs())),
        true);
    request.responseType = 'blob';
    request.setRequestHeader('X-CSRFToken', false);
    request.onload = function (event) {
        var blob = this.response;
        var contentDispo = this.getResponseHeader('Content-Disposition');
        // https://stackoverflow.com/a/23054920/
        var fileName = contentDispo.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)[1];
        saveBlob(blob, fileName);
    }
    request.send(null);
}


function getConditionBtn(n) {
    return `<input id="condt-btn-${n}" type="button" value="Add Condition"/>`
}


function addCondition(n) {
    var expr = prompt('Enter Expression:');
    if (expr) {
        conditions[n] = expr;
        var btn = document.getElementById(`condt-btn-${n}`);
        btn.value = "Edit Condition";
        btn.removeEventListener("click", currentEventHandlers[`condt-btn-${n}`])
        var newlistner = function () { editCondition(n) };
        btn.addEventListener("click", newlistner);
        currentEventHandlers[`condt-btn-${n}`] = newlistner;
    }
}

function editCondition(n) {
    var expr = prompt("Enter Expression:", conditions[`${n}`]);
    if (expr) {
        conditions[n] = expr;
    }
    else if (expr === "") {
        conditions[n] = "";
        var btn = document.getElementById(`condt-btn-${n}`);
        btn.value = "Add Condition";
        btn.removeEventListener("click", currentEventHandlers[`condt-btn-${n}`])
        var newlistner = function () { addCondition(n) };
        btn.addEventListener("click", newlistner);
        currentEventHandlers[`condt-btn-${n}`] = newlistner;
    }

}

function renderPreview() {
    var innerHTML = "<p>\n";
    for (var i = 0; i < previewHTML.length; i++) {
        innerHTML += getConditionBtn(i) + "\t" + previewHTML[i] + "</br>";
    }
    innerHTML += "</p>"
    document.getElementById("template-preview").innerHTML = innerHTML;

    // add listeners to conditionals
    for (let i = 0; i < previewHTML.length; i++) {
        var btnkey = `condt-btn-${i}`
        var btn = document.getElementById(btnkey)
        // check if condition already exists
        if ((!(i in conditions)) || (conditions[i] === "")) {
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
    }
}

function textAreaCallback(payload) {
    nlg_template.push(payload.text);
    var tokenmap = payload.tokenmap;

    var highlighted = payload.text;
    for (let [token, tmpl] of Object.entries(tokenmap)) {
        highlighted = highlighted.replace(`{{ ${tmpl} }}`,
            `<span style=\"background-color:#c8f442\" title="{{ ${tmpl} }}">${token}</span>`);
    }
    previewHTML.push(highlighted);

    // var highlighted = text.replace(/({{[^{}]+}})/g,
    // '<span style=\"background-color:#c8f442\">$1</span>');
    renderPreview();
    document.getElementById("textbox").value = "";
}