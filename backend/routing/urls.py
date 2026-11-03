from django.urls import path

from routing.views import HealthView, HeatmapView, RoutePlanView

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('route-plan/', RoutePlanView.as_view(), name='route-plan'),
    path('heatmap/', HeatmapView.as_view(), name='heatmap'),
]
