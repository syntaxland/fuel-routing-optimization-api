from django.urls import path
from .views import OptimalRouteView

urlpatterns = [
    path('route/', OptimalRouteView.as_view(), name='optimal_route'),
]
