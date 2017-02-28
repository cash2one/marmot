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
    jQuery("html, body").animate({scrollTop:0}, scrollSpeed);
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
