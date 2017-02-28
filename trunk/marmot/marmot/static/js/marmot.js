/**
 * Created by baixue
 */

bootbox.setLocale("zh_CN");

function activeConfirm(url) {
    bootbox.confirm('确认激活吗？', function (result) {
        if (result) {
            $.getJSON(url, {}, function (ret) {
                if (ret.msg == 0) {
                    location.reload();
                } else {
                    bootbox.alert(ret.msg);
                }
            });
        }
    });
}

function deleteConfirm(url) {
    bootbox.confirm('确认删除吗？', function (result) {
        if (result) {
            $.getJSON(url, {}, function (ret) {
                if (ret.msg == 0) {
                    location.reload();
                } else {
                    bootbox.alert(ret.msg);
                }
            });
        }
    });
}

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

jQuery.postJSON = function(url, args, callback) {
    args._xsrf = getCookie("_xsrf");
    $.ajax({url: url, data: JSON.stringify(args), dataType: "json", type: "POST",
            success: function(response) {
        if (callback) callback(response);
    }, error: function(response) {
        console.log("ERROR:", response);
    }});
};

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {};
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

jQuery.fn.disable = function() {
    this.enable(false);
    return this;
};

jQuery.fn.enable = function(opt_enable) {
    if (arguments.length && !opt_enable) {
        this.attr("disabled", "disabled");
    } else {
        this.removeAttr("disabled");
    }
    return this;
};

function openNewWindow(url){
    window.open(url);
}

function loading(flag){
    var oLoading = $('#loading');
    if (oLoading){
        if(flag){
            oLoading.css('display', 'block');
        }else{
            oLoading.css('display', 'none');
        }
    }
}

function uuid(len, radix) {
    var chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.split('');
    var uuid = [], i;
    radix = radix || chars.length;

    if (len) {
        // Compact form
        for (i = 0; i < len; i++) uuid[i] = chars[0 | Math.random()*radix];
    } else {
        // rfc4122, version 4 form
        var r;

        // rfc4122 requires these characters
        uuid[8] = uuid[13] = uuid[18] = uuid[23] = '-';
        uuid[14] = '4';

        // Fill in random data.  At i==19 set the high bits of clock sequence as
        // per rfc4122, sec. 4.1.5
        for (i = 0; i < 36; i++) {
            if (!uuid[i]) {
                r = 0 | Math.random()*16;
                uuid[i] = chars[(i == 19) ? (r & 0x3) | 0x8 : r];
            }
        }
    }
    return uuid.join('');
}
// uuid(8, 2)  => "01001010"
// uuid(8, 10) => "47473046"
// uuid(8, 16) => "098F4D35"

/**
 *	Back To Top Button
 */

var pxShow = 300;  // height on which the button will show
var fadeInTime = 400;  // how slow/fast you want the button to show
var fadeOutTime = 400;  // how slow/fast you want the button to hide
var scrollSpeed = 300;  // how slow/fast you want the button to scroll to top. can be a value, 'slow', 'normal' or 'fast'

// Show or hide the sticky footer button
jQuery(window).scroll(function() {
    if (jQuery(window).scrollTop() >= pxShow) {
        jQuery("#go-top").fadeIn(fadeInTime);
    } else {
        jQuery("#go-top").fadeOut(fadeOutTime);
    }
});

// Animate the scroll to top
jQuery("#go-top a").click(function() {
    jQuery("html, body").animate({scrollTop: 0}, scrollSpeed);
    return false;
});


function backpage(){
    location.href = document.referrer;
}

function backtopage(){
    history.go(-1);
    // window.location.reload(true);
    // document.location.reload();
}