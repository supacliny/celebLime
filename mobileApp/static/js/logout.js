window.fbAsyncInit = function() {

    FB.init({
        appId      : '374652432558901',
        status     : true,
        cookie     : true,
        xfbml      : true,
        oauth      : true,
    });

    function logout(response) {

        // user already logged out of facebook.
        if (!response.session) {
            var button = document.getElementById('fb-auth');
            button.onclick = function() {
                FB.logout(function(response) {
                    $.cookies.erase("fb_auth","/");
                    $.cookies.erase("fb_id","/");
                    $.cookies.erase("fbsr_374652432558901", "/");
                    $.cookies.erase("session", "/");
                    window.location = "/celebLime";
                });            
            };
        return;
        };

        // user currently logged into facebook.
        if (response.status === 'connected') {
            var button = document.getElementById('fb-auth');
            button.onclick = function() {
                FB.logout(function(response) {
                    $.cookies.erase("fb_auth","/");
                    $.cookies.erase("fb_id","/");
                    $.cookies.erase("fbsr_374652432558901", "/");
                    $.cookies.erase("session", "/");
                    window.location = "/celebLime";
                });            
            };
        };

        // user has not authorized celebLime on facebook.
        if (response.status === 'not_authorized') {
            var button = document.getElementById('fb-auth');
            button.onclick = function() {
                FB.logout(function(response) {
                    $.cookies.erase("fb_auth","/");
                    $.cookies.erase("fb_id","/");
                    $.cookies.erase("fbsr_374652432558901", "/");
                    $.cookies.erase("session", "/");
                    window.location = "/celebLime";
                });            
            };
        };

        // user currently logged out facebook.
        if (response.status === 'unknown') {
            var button = document.getElementById('fb-auth');
            button.onclick = function() {
                FB.logout(function(response) {
                    $.cookies.erase("fb_auth","/");
                    $.cookies.erase("fb_id","/");
                    $.cookies.erase("fbsr_374652432558901", "/");
                    $.cookies.erase("session", "/");
                    window.location = "/celebLime";
                });            
            };
        };
    };

    FB.getLoginStatus(logout);
};

(function(d){
    var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
    js = d.createElement('script'); js.id = id; js.async = true;
    js.src = "//connect.facebook.net/en_US/all.js";
    d.getElementsByTagName('head')[0].appendChild(js);
}(document));