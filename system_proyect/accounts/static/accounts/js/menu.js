/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
/* <--- hecho por claude code: se retiró el modo oscuro; el sistema queda siempre claro. */
if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});});}
