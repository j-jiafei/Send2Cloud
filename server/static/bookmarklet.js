
(function() {
var doc = top.document,
iframe = doc.getElementById("bitmark_yoself_fool"),
script = doc.getElementById("bitmark_js");
if (iframe && script) {
alert("bitmarklet is already running... \n close it out first if you want to start over")
return;
}
if (iframe && iframe.parentNode) {
iframe.parentNode.removeChild(iframe);
}
if (script && script.parentNode) {
script.parentNode.removeChild(script);
}
var u = top.location.href,
t = doc.title;
var target_el = getTargetEl(),
target_el_body = target_el.body,
iframe = document.createElement("iframe"),
script = doc.getElementById("bitmark_js"),
iframe_id = "bitmark_yoself_fool",
body_old_className = target_el_body.className || "";
target_el_body.className = [body_old_className, "bitmarklet_on"].join(" ");
var text;
try {
text = getSelectedText();
} catch (ex) {}
iframe.setAttribute("id", iframe_id);
iframe.setAttribute("frameBorder", "0");
iframe.setAttribute("allowTransparency", "true");
iframe.cssText = iframe.style.cssText = "position: fixed; height: 0; width: 0; top: 0; right: 0; z-index: 999999999;";
var urlfrag = "/send?u=" + encodeURIComponent(u);
url = "http://localhost:8080"+urlfrag;
iframe.setAttribute("src", url);
target_el_body.appendChild(iframe);
var loads = 0;
var close_timer = null;
var required_origin = "http://localhost:8080";
var on_msg = function(e) {
e = e || window.event;
if (e.origin == required_origin) {
var msg = e.data;
if (!!~msg.search(/nyanbox:opened/)) {
iframe.style.height = "100%";
iframe.style.width = "100%";
iframe.style.visibility = "visible";
}
else if (!!~msg.search(/nyanbox:close/)) {
setTimeout(clear, 500);
}
else if (!!~msg.search(/nyanbox:mode_change/)) {
var splits = msg.split(":"),
height = splits[3],
mode = splits[2];
if(mode==="confirmation") {
iframe.style.height = height+"px";
iframe.style.width = "660px";
}
}
}
}
removeEvent(window, "message", on_msg);
addEvent(window, "message", on_msg);
var right = 0;
function clear() {
removeEvent(window, "message", on_msg);
if (iframe && iframe.parentNode) iframe.parentNode.removeChild(iframe);
if (script && script.parentNode) script.parentNode.removeChild(script);
target_el_body.className = body_old_className;
}
function addEvent(obj, type, fn) {
return obj.attachEvent ? obj.attachEvent('on' + type, fn) : obj.addEventListener(type, fn, false);
}
function removeEvent(obj, type, fn) {
return obj.detachEvent ? obj.detachEvent('on' + type, fn) : obj.removeEventListener(type, fn, false);
}
function getSelectedText() {
var txt = '';
if ((target_el === doc) && window.getSelection) txt = window.getSelection();
else if (document.getSelection) txt = target_el.getSelection();
else if (document.selection) txt = target_el.selection.createRange().text;
else return '';
if (txt.toString()) {
txt = txt.toString().replace(/^ +| +$/g, "");
var add_quotes = true;
txt = txt.toString();
if (txt.charAt(0) === "\u201c" || txt.charAt(0) === "\"" || txt.charAt(0) === "“" || txt.toLowerCase().indexOf("&quot;") === 0 || txt.toLowerCase().indexOf("&ldquo;") === 0) {
if (txt.charAt(txt.length - 1) === "\u201c" || txt.charAt(txt.length - 1) === "\"" || txt.charAt(txt.length - 1) === "”" || txt.toLowerCase().indexOf("&quot;") === txt.length - 6 || txt.toLowerCase().indexOf("&rdquo;") === txt.length - 7) {
add_quotes = false;
}
}
if (add_quotes) {
txt = "\u201c" + txt + "\u201d";
}
}
return txt;
}
function getTargetEl() {
var is_frameset = doc.getElementsByTagName("frameset").length;
if (!is_frameset) {
return doc;
}
var frames = doc.getElementsByTagName("frame"),
biggest_frame, max_area = 0,
frame_doc, area;
for (var i = 0, len = frames.length; i < len; i++) {
frame_doc = frames[i]; //.document;
try {
area = frame_doc.height * frame_doc.width;
if (area > max_area) {
max_area = area;
biggest_frame = frame_doc;
}
} catch (ex) {}
}
return biggest_frame.contentDocument || biggest_frame;
}
try {
var style_obj;
// if there is not already a stylesheet to be used for the app (first time this gets created) create one
if (!doc.getElementById("bitmark_stylesheet")) {
var style_el = document.createElement("style");
style_el.id = "bitmark_stylesheet";
style_el.type = "text/css";
doc.getElementsByTagName("head")[0].appendChild(style_el);
style_obj = doc.getElementById("bitmark_stylesheet").sheet;
} else {
style_obj = doc.getElementById("bitmark_stylesheet").sheet;
}
if (!style_obj) {
style_obj = doc.styleSheets[doc.styleSheets.length - 1];
}
var selector = ["#bitmark_yoself_fool"],
styles = ["visibility: visible !important; display: block !important;"];
selector.push("body.bitmarklet_on");
styles.push("overflow:hidden;");
if (navigator.userAgent.toLowerCase().indexOf("chrome") > -1) {
selector.push("body.bitmarklet_on iframe,body.bitmarklet_on embed,body.bitmarklet_on object");
styles.push("visibility:hidden;");
}
for (var i = 0, len = selector.length; i < len; i++) {
if (style_obj.insertRule) {
style_obj.insertRule(selector[i] + ' {' + styles[i] + '}', style_obj.cssRules.length);
} else if (style_obj.addRule) {
style_obj.addRule(selector[i], styles[i], -1);
}
}
} catch (ex) {}
})();

