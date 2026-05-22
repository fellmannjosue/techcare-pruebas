document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('form input, form textarea, form select').forEach(function(el){
    if (el.type === 'checkbox') el.classList.add('form-check-input');
    else if (el.tagName === 'SELECT' && !el.classList.contains('form-control')) el.classList.add('form-select');
    else if (!el.classList.contains('form-control')) el.classList.add('form-control');
  });
});
