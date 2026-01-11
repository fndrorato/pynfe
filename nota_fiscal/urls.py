# URL relacionandas aos clientes
from django.urls import path
from . import views

urlpatterns = [
    path('nota-fiscal/', views.NotaFiscalView.as_view(), name='nota-fiscal-list-create'),
    path('nota-fiscal/buscar-retorno/', views.NotaFiscalDetailView.as_view(), name='nota-fiscal-detail'),
    path('nota-fiscal/consultar/', views.NotaFiscalConsultarView.as_view(), name='nota-fiscal-detail'),
    path('nota-fiscal/cce/', views.NotaFiscalCCeView.as_view(), name='nota-fiscal-cce'),
    path('nota-fiscal/cancelar/', views.NotaFiscalCancelarView.as_view(), name='nota-fiscal-cancelar'),
    path('nota-fiscal/email/', views.NotaFiscalSendEmailView.as_view(), name='nota-fiscal-enviar-email'),
    path('nota-fiscal/inutilizar/', views.NotaFiscalInutilizarView.as_view(), name='nota-fiscal-inutilizar'),
]
