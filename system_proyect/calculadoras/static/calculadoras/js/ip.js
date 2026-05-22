// Populate CIDR select
for (let i = 0; i <= 32; i++) {
  $('#inp-cidr').append(`<option value="${i}" ${i===24?'selected':''}>/${i}</option>`);
}

function ipToInt(ip) {
  return ip.split('.').reduce((acc, oct) => (acc << 8) + parseInt(oct), 0) >>> 0;
}
function intToIp(n) {
  return [(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255].join('.');
}
function toBinary(ip) {
  return ip.split('.').map(o => parseInt(o).toString(2).padStart(8,'0')).join('.');
}
function ipClase(ip) {
  const first = parseInt(ip.split('.')[0]);
  if (first < 128) return 'A'; if (first < 192) return 'B';
  if (first < 224) return 'C'; if (first < 240) return 'D'; return 'E';
}

$('#btn-calcular-ip').on('click', function(){
  const ip = $('#inp-ip').val().trim();
  const cidr = parseInt($('#inp-cidr').val());
  const parts = ip.split('.');
  if (parts.length !== 4 || parts.some(p => isNaN(p) || p < 0 || p > 255)) {
    Swal.fire({icon:'warning', title:'IP inválida', text:'Ingresa una dirección IPv4 válida.'}); return;
  }
  const ipInt = ipToInt(ip);
  const maskInt = cidr === 0 ? 0 : (0xFFFFFFFF << (32 - cidr)) >>> 0;
  const networkInt = (ipInt & maskInt) >>> 0;
  const broadcastInt = (networkInt | (~maskInt >>> 0)) >>> 0;
  const hosts = cidr >= 31 ? (cidr === 32 ? 1 : 2) : Math.pow(2, 32 - cidr) - 2;
  const firstHost = cidr >= 31 ? networkInt : networkInt + 1;
  const lastHost = cidr >= 31 ? broadcastInt : broadcastInt - 1;

  $('#res-ip').removeClass('d-none');
  $('#res-network').text(intToIp(networkInt) + '/' + cidr);
  $('#res-broadcast').text(intToIp(broadcastInt));
  $('#res-hosts').text(hosts.toLocaleString());
  $('#res-mask').text(intToIp(maskInt));
  $('#res-wildcard').text(intToIp(~maskInt >>> 0));
  $('#res-clase').text('Clase ' + ipClase(ip));
  $('#res-rango').text(intToIp(firstHost) + ' – ' + intToIp(lastHost));
  $('#res-binario').text(toBinary(ip));
});

$('#inp-ip').on('keydown', function(e){ if(e.key==='Enter') $('#btn-calcular-ip').click(); });
