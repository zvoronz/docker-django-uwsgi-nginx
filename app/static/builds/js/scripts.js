
$('img').attr('draggable',"false");

// show modal with a question text.
function confirm(event, question, callback, url) {
	document.getElementById('question_text').innerHTML = question;

	if (callback)
		document.getElementById('question_ok').setAttribute('onclick', callback);
	else
		document.getElementById('question_ok').removeAttribute('onclick');

	if (url)
		document.getElementById('question_ok').setAttribute('href', url);
	else
		document.getElementById('question_ok').setAttribute('href', '#');

	 $('#modal-question').modal('show');
}