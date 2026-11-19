import os

from django import forms
from django.core.files.uploadedfile import UploadedFile
from .models import Ticket, TicketComment

# <--- hecho por claude code (seguridad 05-nov-2026): adjuntos solo de tipos conocidos (antes cualquier archivo, también .html/.svg, y se servía desde el mismo dominio)
EXT_ADJUNTO_PERMITIDAS = frozenset({
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',                # imágenes  # <--- hecho por claude code (seguridad 05-nov-2026): + webp (raster seguro; los input image/* lo ofrecen)
    'pdf',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf',
    'txt', 'csv',
    'zip', 'rar', '7z',
})
ADJUNTO_MAX_BYTES = 15 * 1024 * 1024   # 15 MB (mismo límite que el chat)
# <--- hecho por claude code (seguridad 05-nov-2026): el atributo accept de los selectores de archivo sale de la MISMA lista blanca (tipos MIME de imagen para que el móvil siga ofreciendo la galería + extensiones)
ACCEPT_IMAGENES = 'image/jpeg,image/png,image/gif,image/bmp,image/webp'
ACCEPT_ADJUNTOS = ACCEPT_IMAGENES + ',' + ','.join('.' + e for e in sorted(EXT_ADJUNTO_PERMITIDAS))


def validar_adjunto(archivo):
    """<--- hecho por claude code (seguridad 05-nov-2026): None si el archivo es aceptable; si no, el texto del error."""
    nombre = os.path.basename(getattr(archivo, 'name', '') or '')
    ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
    if ext not in EXT_ADJUNTO_PERMITIDAS:
        return ('Tipo de archivo no permitido (.%s). Se aceptan imágenes JPG/PNG/GIF/BMP/WEBP, PDF, '
                'documentos de Office, TXT/CSV y ZIP/RAR/7Z.' % (ext or '?'))
    if (getattr(archivo, 'size', 0) or 0) > ADJUNTO_MAX_BYTES:
        return 'El archivo supera el límite de 15 MB.'
    return None


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        # <--- hecho por claude code: la urgencia la elige el usuario al crear el ticket
        fields = ['name', 'grade', 'email', 'urgencia', 'description', 'comments', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'grade': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'urgencia': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {'urgencia': 'Nivel de urgencia'}

    def clean_attachment(self):
        # <--- hecho por claude code (seguridad 05-nov-2026): valida tipo y tamaño del adjunto nuevo
        f = self.cleaned_data.get('attachment')
        if isinstance(f, UploadedFile):
            err = validar_adjunto(f)
            if err:
                raise forms.ValidationError(err)
        return f

def _clean_archivo_admin(form, campo):
    # <--- hecho por claude code (seguridad 05-nov-2026): el admin también subía cualquier archivo a media/ (sin lista blanca); misma validación que el formulario público y el chat
    f = form.cleaned_data.get(campo)
    if isinstance(f, UploadedFile):
        err = validar_adjunto(f)
        if err:
            raise forms.ValidationError(err)
    return f


class TicketAdminForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = '__all__'

    def clean_attachment(self):
        return _clean_archivo_admin(self, 'attachment')


class TicketCommentAdminForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = '__all__'

    def clean_archivo(self):
        return _clean_archivo_admin(self, 'archivo')


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['mensaje']  # Solo mensaje, el resto lo pone el view
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Escribe tu comentario aquí...',
            }),
        }
        labels = {
            'mensaje': 'Comentario',
        }
