// The piece of code is adapted from bitly.com/a/bitmarklet.js
(function() {
  var doc = top.document;
  var iframe = doc.getElementById("send2cloud_iframe");
  var script = doc.getElementById("send2cloud_js");
  if (iframe && script) {
    alert("send2cloud is running... \nClose it first if you want to start it over");
    return;
  }
  if (iframe && iframe.parentNode) {
    iframe.parentNode.removeChild(iframe);
  }
  if (script && script.parentNode) {
    script.parentNode.removeChild(script);
  }
  var u = top.location.href;
  var target_el = getTargetEl();
  var target_el_body = target_el.body;
  var iframe = document.createElement("iframe");
  var script = doc.getElementById("send2cloud_js");
  var iframe_id = "send2cloud_iframe";
  var body_old_className = target_el_body.className || "";
  target_el_body.className = [body_old_className, "send2cloud_on"].join(" ");
  iframe.setAttribute("id", iframe_id);
  iframe.setAttribute("frameBorder", "0");
  iframe.setAttribute("allowTransparency", "true");
  iframe.cssText = iframe.style.cssText = "position: fixed; height: 0; width: 0; top: 0; right: 0; z-index: 999999999;";
  var urlfrag = "/send?u=" + encodeURIComponent(u);
  url = "http://send2cloud-server.appspot.com"+urlfrag;
  iframe.setAttribute("src", url);
  target_el_body.appendChild(iframe);
  var required_origin = "http://send2cloud-server.appspot.com";
  var on_msg = function(e) {
    e = e || window.event;
    if (e.origin == required_origin) {
      var msg = e.data;
      if (!!~msg.search(/send2cloudbox:opened/)) {
        iframe.style.height = "100%";
        iframe.style.width = "100%";
        iframe.style.visibility = "visible";
      }
      else if (!!~msg.search(/send2cloudbox:close/)) {
        setTimeout(clear, 500);
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
    if (!doc.getElementById("send2cloud_stylesheet")) {
      var style_el = document.createElement("style");
      style_el.id = "send2cloud_stylesheet";
      style_el.type = "text/css";
      doc.getElementsByTagName("head")[0].appendChild(style_el);
      style_obj = doc.getElementById("send2cloud_stylesheet").sheet;
    } else {
      style_obj = doc.getElementById("send2cloud_stylesheet").sheet;
    }
    if (!style_obj) {
      style_obj = doc.styleSheets[doc.styleSheets.length - 1];
    }
    var selector = ["#send2cloud_iframe"],
    styles = ["visibility: visible !important; display: block !important;"];
    selector.push("body.send2cloud_on");
    styles.push("overflow:hidden;");
    if (navigator.userAgent.toLowerCase().indexOf("chrome") > -1) {
      selector.push("body.send2cloud_on iframe,body.send2cloud_on embed,body.send2cloud_on object");
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

