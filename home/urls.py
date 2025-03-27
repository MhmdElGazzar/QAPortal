from django.urls import path
from .views import (
    HomePageView, 
    CreateQualityTasksView, 
    CreateAzureTaskAPIView, 
    SettingsView, 
    EstimateStoryView,
    ProjectInfoView
)

urlpatterns = [
    path('estimate-story/', EstimateStoryView.as_view(), name='estimate_story'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('', HomePageView.as_view(), name='home'),
    path('create-quality-tasks/', CreateQualityTasksView.as_view(), name='create_quality_tasks'),
    path('project-info/', ProjectInfoView.as_view(), name='project_info'),
    path('api/create-azure-task/', CreateAzureTaskAPIView.as_view(), name='create_azure_task'),
]
