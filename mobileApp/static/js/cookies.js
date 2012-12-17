// http://www.quirksmode.org/js/cookies.html cookies
$.cookies = {
    create: function (name, value, seconds, path) {
        var expires, date;
        path = path || '/';
        if (seconds) {
            date = new Date();
            date.setTime(date.getTime() + (seconds*1000));
            expires = '; expires=' + date.toGMTString();
        }
        else {
            expires = '';
        }
        document.cookie = name + '=' + value + expires + '; path=' + path;
    },
    read: function(name) {
        var nameEQ = name + '=',
            ca = document.cookie.split(';'),
            c;
        for (var i=0, len=ca.length; i<len; i++) {
            c = ca[i];
            while (c.charAt(0)==' ') {
                c = c.substring(1, c.length);
            }
            if (c.indexOf(nameEQ) === 0) {
                return c.substring(nameEQ.length, c.length);
            }
        }
        return null;
    },
    erase: function(name, path) {
        this.create(name, '', -1, path);
    }
};