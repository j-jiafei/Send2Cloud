// The piece of code is adapted from http://coding.smashingmagazine.com/2010/05/23/make-your-own-bookmarklets-with-jquery/
(function() {
  // the minimum version of jQuery we need
  var v = "1.3.2";

  // check prior inclusion of jQuery we want
  if (window.jQuery == undefined || window.jQuery.fn.jquery < v) {
    var done = false;
    var script = document.createElement("script");
    script.src = "//ajax.googleapis.com/ajax/libs/jquery/" + v + "/jquery.min.js";
    script.onload = script.onreadystatechange = function() {
      if (!done && (!this.readyState || this.readyState == "loaded" || this.readyState == "complete")) {
        done = true;
        initMyBookmarklet();
      }
    };
    if (document.getElementsByTagName("head")[0]) {
      document.getElementsByTagName("head")[0].appendChild(script);
    }
    else {
      document.getElementsByTagName("body")[0].appendChild(script);
    }
  } else {
    initMyBookmarklet();
  }

  function initMyBookmarklet() {
    (window.send2cloud_bookmarklet = function() {
      if ($("#s2cframe").length == 0) {
        var u = window.location.href;
        if (u != "" && u != null) {
          $("body").append("\
            <div id='s2cframe'>\
              <div id='s2cframe_veil' style=''>\
              </div>\
              <iframe src='//localhost:8080/send?u=" + u + "' onload=\"$('#s2cframe iframe').slideDown(500);\">Enable iFrames.</iframe>\
              <style type='text/css'>\
                #s2cframe_veil { display: none; position: fixed; width: 100%; height: 100%; top: 0; left: 0; background-color: rgba(255,255,255,.25); cursor: pointer; z-index: 900; }\
                #s2cframe iframe { display: none; position: fixed; top: 10%; left: 30%; width: 40%; height: 30%; z-index: 999; border: 10px solid rgba(0,0,0,.5); margin= -5px 0 0 -5px; }\
              </style>\
            </div>");
            $("#s2cframe_veil").fadeIn(750);
        }
      }
      else {
        $("#s2cframe_veil").fadeOut(750);
        $("#s2cframe iframe").slideUp(500);
        setTimeout("$('#s2cframe').remove()", 750);
      }
      $("#s2cframe_veil").click(function(event) {
        $("#s2cframe_veil").fadeOut(750);
        $("#s2cframe iframe").slideUp(500);
        setTimeout("$('#s2cframe').remove()", 750);
      });
    })();
  }
})();
