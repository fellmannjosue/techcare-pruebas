from django import forms
from .models import Ticket, TicketComment

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
