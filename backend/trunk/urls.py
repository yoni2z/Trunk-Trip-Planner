from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet

router = DefaultRouter()
router.register(r'trips', TripViewSet, basename='trip')

urlpatterns = [
    path('', include(router.urls)),
    path('trips/<uuid:pk>/print-logs/', TripViewSet.as_view({'get': 'print_logs'}), name='print-logs'),
]