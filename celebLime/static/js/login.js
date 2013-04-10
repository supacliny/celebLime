window.fbAsyncInit = function() {

    FB.init({
        appId      : '374652432558901',
        status     : true,
        cookie     : true,
        xfbml      : true,
        oauth      : true,
    });

    function login(response) {

        // currently logged in to facebook.
        if (response.status === 'connected') {

            var button = document.getElementById('fb-auth');
            if (button == null) {return 0;}
            button.onclick = function() {
                FB.login(function(response) {
                    if (response.authResponse) {
                        var AuthResponse = FB.getAuthResponse();
                        $.cookies.create("fb_auth", AuthResponse.accessToken,0,"/");
                        $.cookies.create("fb_id", AuthResponse.userID, 0, "/");
                        window.location = "/celebLime/manage";
                    } else {
                    // user pressed cancel on the login auth dialog
                    }
                }, {scope: 'email,user_birthday'});            
            };
        };

        // not currently logged in to facebook so pop-up opens!
        if (response.status === 'unknown') {
            var button = document.getElementById('fb-auth');
            if (button == null) {return 0;}
            button.onclick = function() {
                FB.login(function(response) {
                    if (response.authResponse) {
                        var AuthResponse = FB.getAuthResponse();
                        $.cookies.create("fb_auth", AuthResponse.accessToken,0,"/");
                        $.cookies.create("fb_id", AuthResponse.userID, 0, "/");
                        window.location = "/celebLime/manage";
                    } else {
                    // user pressed cancel on the login auth dialog
                    }
                }, {scope: 'email,user_birthday'});            
            };
        };
    };

    FB.getLoginStatus(login);
};

(function(d){
    var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
    js = d.createElement('script'); js.id = id; js.async = true;
    js.src = "//connect.facebook.net/en_US/all.js";
    d.getElementsByTagName('head')[0].appendChild(js);
}(document));
