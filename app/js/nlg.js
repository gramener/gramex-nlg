function parseUrlFromHref() {
    var location = window.location;
    var prefix = location.protocol + '//' + location.hostname + ':' + location.port + location.pathname;
    return location.href.replace(prefix, '')
}

function setDataArgs(x) {
    df = x.formdata;
    args = parseUrlFromHref();
}

function processTemplate() {
    var tbox = document.getElementById("textbox");
    var request = new XMLHttpRequest();
    request.onreadystatechange = function() {
        if (request.readyState == 4 && request.status == 200)
            textAreaCallback(request.responseText);
    }
    var url = "/textproc?" + decodeURIComponent(args.replace('#', ''));
    request.open("POST", url, true);
    var payload = {"data": df, "text": tbox.value};
    request.send(JSON.stringify(payload));
}

function saveBlob(blob, fileName) {
    console.log('start saveblob');
    var a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = fileName;
    // click working with firefox & chrome: https://stackoverflow.com/a/22469115/
    a.dispatchEvent(new MouseEvent('click', {
        'view': window,
        'bubbles': true,
        'cancelable': false
    }));
    console.log('end saveblob');
}

function downloadTemplate() {
    console.log('Start sending req.')
    var request = new XMLHttpRequest();
    request.open('GET', "/tmpl-download?tmpl=" + encodeURIComponent(nlg_template), true);
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
    console.log('end download func!');
}

function textAreaCallback(responseText) {
    var payload = JSON.parse(responseText);
    nlg_template = payload.text;
    var tokenmap = payload.tokenmap;

    var highlighted = payload.text;
    var hghlt_tmpl = `<span style="background-color:#c8f442">`
    for (let [token, tmpl] of Object.entries(tokenmap)) {
        highlighted = highlighted.replace(`{{ ${tmpl} }}`,
            `<span style=\"background-color:#c8f442\" title="${token}">{{ ${tmpl} }}</span>`);
    }

    // var highlighted = text.replace(/({{[^{}]+}})/g,
        // '<span style=\"background-color:#c8f442\">$1</span>');
    document.getElementById("template-preview").innerHTML = highlighted;
}