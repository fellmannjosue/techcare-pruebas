# core/email_backend_pruebas.py
# <--- hecho por claude code (10-nov-2026): correo de PRUEBAS con LISTA BLANCA.
"""Pruebas usa la misma base de usuarios que producción (correos reales). Este backend envía por SMTP
SOLO a los destinatarios de la lista blanca (env ``EMAILS_PRUEBA_PERMITIDOS``, separados por coma;
por defecto ``jfellmann@ana-hn.org``). A cualquier otro destinatario no le llega: el correo se escribe
en el log del contenedor (como el backend de consola) con la marca [PRUEBAS · NO ENVIADO].

Se usa también para las conexiones propias de Enfermería/Coordinación (core/email_utils.py), que antes
forzaban SMTP y sí enviaban de verdad desde pruebas.
"""
import copy
import os
import sys

from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend


def permitidos():
    crudo = os.getenv('EMAILS_PRUEBA_PERMITIDOS', 'jfellmann@ana-hn.org')
    return {c.strip().lower() for c in crudo.split(',') if c.strip()}


def _correo(dir_):
    d = (dir_ or '').strip()
    if '<' in d and '>' in d:
        d = d[d.index('<') + 1:d.index('>')]
    return d.lower()


class ListaBlancaBackend(SMTPBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        ok = permitidos()
        enviar, retener = [], []
        for m in email_messages:
            to = [d for d in m.to if _correo(d) in ok]
            cc = [d for d in m.cc if _correo(d) in ok]
            bcc = [d for d in m.bcc if _correo(d) in ok]
            fuera = [d for d in (m.to + m.cc + m.bcc) if _correo(d) not in ok]
            if to or cc or bcc:
                m2 = copy.copy(m)
                m2.to, m2.cc, m2.bcc = to, cc, bcc
                enviar.append(m2)
            if fuera:
                m3 = copy.copy(m)
                m3.to, m3.cc, m3.bcc = fuera, [], []
                retener.append(m3)
        n = 0
        if retener:
            sys.stdout.write('[PRUEBAS · NO ENVIADO: fuera de EMAILS_PRUEBA_PERMITIDOS]\n')
            ConsoleBackend(stream=sys.stdout).send_messages(retener)
        if enviar:
            n = super().send_messages(enviar) or 0
            sys.stdout.write(f'[PRUEBAS · ENVIADO por SMTP a lista blanca: {n} correo(s)]\n')
        return n or len(retener)
