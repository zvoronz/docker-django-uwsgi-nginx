
function save_config() {

		var options = {};

		var app_settings_list = document.getElementsByClassName('application_settings');
		var access_list = [];
		for (q=0; q<app_settings_list.length; q++) 
		{
			var temp = {};
			temp.application = app_settings_list[q].id;
			temp.credentials_list = app_settings_list[q].getElementsByTagName('textarea')[0].value;
			temp.limited_access = app_settings_list[q].getElementsByTagName('input')[0].checked;
			access_list.push(temp);
		}
		options['access'] = access_list;

		var json_obj = JSON.stringify(options);

		var xhttp = new XMLHttpRequest();
		xhttp.open("POST", '/access/save/settings', true);
		xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
		var csrftoken = getCookie('csrftoken');
		xhttp.setRequestHeader("X-CSRFToken", csrftoken);
		
		xhttp.send("json_obj=" + encodeURIComponent(json_obj));

		xhttp.onload = function () 
		{
			if ((this.status == 200) && (this.responseText=='Ok')) 
				document.location.href = "/choose";
			else 
				alert('Unexpected error.' + this.responseText);
		}
}


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
