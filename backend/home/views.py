from django.views.generic import TemplateView
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import JsonResponse
from pathlib import Path
from .serializers import AzureTaskSerializer
import requests
import base64
import json
import logging
import os
import openai
import re
import html

logger = logging.getLogger(__name__)

def preprocess_text_for_gpt(text):
    """
    Preprocesses text before sending to GPT:
    1. Removes HTML tags
    2. Decodes Unicode escape sequences
    3. Trims whitespace and normalizes newlines
    """
    if not text:
        return text
        
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Decode Unicode escape sequences
    text = text.encode('utf-8').decode('unicode-escape')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    logger.info(f"Preprocessed text: {text}")
    return text

class ProjectInfoView(TemplateView):
    template_name = 'home/project_info.html'

    def get_azure_data(self):
        pat = settings.AZURE_DEVOPS_PAT
        auth = base64.b64encode(f":{pat}".encode()).decode()
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {auth}'
        }

        # Get team members
        members_url = f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/_apis/projects/{settings.AZURE_DEVOPS_PROJECT}/teams?api-version=7.0"
        try:
            logger.info(f"Fetching team members from: {members_url}")
            response = requests.get(members_url, headers=headers)
            logger.info(f"Team members API response status: {response.status_code}")
            team_members = []
            if response.status_code == 200:
                logger.info(f"Team members API response: {response.json()}")
                teams_data = response.json()
                for team in teams_data['value']:
                    team_id = team['id']
                    members_detail_url = f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/_apis/projects/{settings.AZURE_DEVOPS_PROJECT}/teams/{team_id}/members?api-version=7.0"
                    members_response = requests.get(members_detail_url, headers=headers)
                    if members_response.status_code == 200:
                        members = members_response.json()
                        team_members.extend([member['identity']['uniqueName'] for member in members['value']])
        except Exception as e:
            logger.error(f"Error fetching team members: {str(e)}")
            team_members = []

        # Get iteration paths
        iterations_url = f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/{settings.AZURE_DEVOPS_PROJECT}/{settings.AZURE_DEVOPS_PROJECT} Team/_apis/work/teamsettings/iterations?api-version=7.0"
        try:
            logger.info(f"Fetching iterations from: {iterations_url}")
            response = requests.get(iterations_url, headers=headers)
            logger.info(f"Iterations API response status: {response.status_code}")
            iteration_paths = []
            if response.status_code == 200:
                logger.info(f"Iterations API response: {response.json()}")
                iterations_data = response.json()
                iteration_paths = [iteration['path'] for iteration in iterations_data['value']]
        except Exception as e:
            logger.error(f"Error fetching iterations: {str(e)}")
            iteration_paths = []

        return {
            'team_members': team_members,
            'iteration_paths': iteration_paths
        }

    def get(self, request, *args, **kwargs):
        azure_data = self.get_azure_data()
        return render(request, self.template_name, {
            'team_members': azure_data['team_members'],
            'iteration_paths': azure_data['iteration_paths']
        })

class EstimateStoryView(TemplateView):
    template_name = 'home/estimate_story.html'

    def get_azure_story(self, story_id):
        azure_url = f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/{settings.AZURE_DEVOPS_PROJECT}/_apis/wit/workitems/{story_id}?api-version={settings.AZURE_DEVOPS_API_VERSION}"
        pat = settings.AZURE_DEVOPS_PAT
        auth = base64.b64encode(f":{pat}".encode()).decode()
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {auth}'
        }
        
        try:
            response = requests.get(azure_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data['fields'].get('System.Title', ''),
                    'description': data['fields'].get('System.Description', '')
                }
            else:
                logger.error(f"Azure API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error fetching story: {str(e)}")
            return None

    def get_openai_estimates(self, description):
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
         # Preprocess description before sending to GPT
        description = preprocess_text_for_gpt(description)
        try:
            # Load task configurations
            with open('task_config.json', 'r') as f:
                task_configs = json.load(f)
            
            tasks_list = "\n".join([f"- {task['title']}: {task['description']}" for task in task_configs.values()])
            
           
            
            prompt = f"""
            Given this user story description:
            {description}
            
            Please estimate the effort in hours for each of these quality tasks:
            user story review: 
            test design:
            test exeucution:
            bug retest:

            Provide estimates in this format:
            task_name: hours
            """

            messages = [
                {"role": "system", "content": "You are a QA expert who estimates effort for quality tasks."},
                {"role": "user", "content": prompt}
            ]
            
            logger.info("Sending request to OpenAI API")
            logger.info(f"Model: gpt-4")
            logger.info(f"Messages: {json.dumps(messages, indent=2)}")
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            
            logger.info("Received response from OpenAI API")
            logger.info(f"Response: {response.choices[0].message.content}")
            
            # Parse response to get estimates
            estimates = {}
            response_text = response.choices[0].message.content
            
            for task_name in task_configs.keys():
                # Look for task name followed by number in response
                import re
                match = re.search(f"{task_name}:\\s*(\\d+(?:\\.\\d+)?)", response_text)
                if match:
                    estimates[task_name] = float(match.group(1))
                else:
                    estimates[task_name] = 1.0  # Default estimate if not found
                    
            return estimates
            
        except Exception as e:
            logger.error(f"Error getting OpenAI estimates: {str(e)}")
            return None

    def post(self, request, *args, **kwargs):
        story_id = request.POST.get('story_id')
        if not story_id:
            return render(request, self.template_name, {
                'error_message': 'Please provide a story ID'
            })
        
        story_details = self.get_azure_story(story_id)
        if not story_details:
            return render(request, self.template_name, {
                'error_message': 'Failed to fetch story details from Azure'
            })
            
        estimates = self.get_openai_estimates(story_details['description'])
        if not estimates:
            return render(request, self.template_name, {
                'error_message': 'Failed to get estimates from OpenAI'
            })
            
        return render(request, self.template_name, {
            'story_id': story_id,
            'story_title': story_details['title'],
            'story_description': story_details['description'],
            'estimates': estimates
        })

class SettingsView(TemplateView):
    template_name = 'home/settings.html'

    def get(self, request, *args, **kwargs):
        context = {
            'settings': {
                'AZURE_DEVOPS_ORG': settings.AZURE_DEVOPS_ORG,
                'AZURE_DEVOPS_PROJECT': settings.AZURE_DEVOPS_PROJECT,
                'AZURE_DEVOPS_API_VERSION': settings.AZURE_DEVOPS_API_VERSION,
                'AZURE_DEVOPS_PAT': settings.AZURE_DEVOPS_PAT,
                'OPENAI_API_KEY': settings.OPENAI_API_KEY,
            }
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            if request.content_type == 'application/x-www-form-urlencoded':
                data = {
                    'azure_org': request.POST.get('azure_org'),
                    'azure_project': request.POST.get('azure_project'),
                    'azure_api_version': request.POST.get('azure_api_version'),
                    'azure_pat': request.POST.get('azure_pat'),
                    'openai_key': request.POST.get('openai_key')
                }
            else:
                data = json.loads(request.body)
            settings_path = settings.BASE_DIR / 'QAPortal' / 'settings.py'
            
            with open(settings_path, 'r') as f:
                content = f.read()

            # Update settings values using regex
            import re
            patterns = {
                'AZURE_DEVOPS_ORG': r"AZURE_DEVOPS_ORG\s*=\s*['\"]([^'\"]*)['\"]",
                'AZURE_DEVOPS_PROJECT': r"AZURE_DEVOPS_PROJECT\s*=\s*['\"]([^'\"]*)['\"]",
                'AZURE_DEVOPS_API_VERSION': r"AZURE_DEVOPS_API_VERSION\s*=\s*['\"]([^'\"]*)['\"]",
                'AZURE_DEVOPS_PAT': r"AZURE_DEVOPS_PAT\s*=\s*['\"]([^'\"]*)['\"]",
                'OPENAI_API_KEY': r"OPENAI_API_KEY\s*=\s*['\"]([^'\"]*)['\"]"
            }
            
            for key, pattern in patterns.items():
                setting_value = data[key.lower().replace('azure_devops_', 'azure_').replace('openai_api_key', 'openai_key')]
                content = re.sub(pattern, f"{key} = '{setting_value}'", content)

            with open(settings_path, 'w') as f:
                f.write(content)

            # Update runtime settings
            settings.AZURE_DEVOPS_ORG = data['azure_org']
            settings.AZURE_DEVOPS_PROJECT = data['azure_project']
            settings.AZURE_DEVOPS_API_VERSION = data['azure_api_version']
            settings.AZURE_DEVOPS_PAT = data['azure_pat']
            settings.OPENAI_API_KEY = data['openai_key']

            return render(request, self.template_name, {
                'settings': {
                    'AZURE_DEVOPS_ORG': settings.AZURE_DEVOPS_ORG,
                    'AZURE_DEVOPS_PROJECT': settings.AZURE_DEVOPS_PROJECT,
                    'AZURE_DEVOPS_API_VERSION': settings.AZURE_DEVOPS_API_VERSION,
                    'AZURE_DEVOPS_PAT': settings.AZURE_DEVOPS_PAT,
                    'OPENAI_API_KEY': settings.OPENAI_API_KEY,
                },
                'success_message': 'Settings saved successfully!'
            })
        except Exception as e:
            return render(request, self.template_name, {
                'settings': {
                    'AZURE_DEVOPS_ORG': settings.AZURE_DEVOPS_ORG,
                    'AZURE_DEVOPS_PROJECT': settings.AZURE_DEVOPS_PROJECT,
                    'AZURE_DEVOPS_API_VERSION': settings.AZURE_DEVOPS_API_VERSION,
                    'AZURE_DEVOPS_PAT': settings.AZURE_DEVOPS_PAT,
                    'OPENAI_API_KEY': settings.OPENAI_API_KEY,
                },
                'error_message': f'Error saving settings: {str(e)}'
            })

class HomePageView(TemplateView):
    template_name = 'home/home.html'

class CreateQualityTasksView(TemplateView):
    template_name = 'home/create_quality_tasks.html'

    def post(self, request, *args, **kwargs):
        logger.info("Received request to create quality tasks")
        assignee = request.POST.get('assignee')
        userstory_id = request.POST.get('userstory_id')
        iteration_path = request.POST.get('iteration_path')
        tasks = request.POST.getlist('tasks')

        if not tasks:
            logger.error("No tasks selected")
            return render(request, self.template_name, {
                'error_message': 'Please select at least one task'
            })

        # Validate estimates for selected tasks
        missing_estimates = []
        for task_type in tasks:
            estimate = request.POST.get(f'{task_type}_estimate')
            if not estimate:
                missing_estimates.append(task_type)

        if missing_estimates:
            logger.error(f"Missing estimates for tasks: {missing_estimates}")
            return render(request, self.template_name, {
                'error_message': f'Please provide estimates for: {", ".join(missing_estimates)}'
            })

        # Load task configurations
        try:
            with open('task_config.json', 'r') as f:
                task_configs = json.load(f)
            logger.info("Task configurations loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load task configurations: {str(e)}")
            return render(request, self.template_name, {
                'error_message': 'Failed to load task configurations'
            })

        created_tasks = []
        failed_tasks = []

        # Create API instance
        api = CreateAzureTaskAPIView()

        # Create each selected task
        for task_type in tasks:
            if task_type in task_configs:
                task_config = task_configs[task_type]
                estimate = request.POST.get(f'{task_type}_estimate', 0)
                task_data = {
                    'title': task_config['title'],
                    'description': task_config['description'],
                    'activity': task_config['activity'],
                    'original_estimate': float(estimate) if estimate else 0,
                    'remaining_work': float(estimate) if estimate else 0,
                    'assigned_to': assignee,
                    'iteration_path': iteration_path,
                    'user_story_id': int(userstory_id)
                }

                # Create mock request with data and headers
                class MockRequest:
                    def __init__(self, data, headers):
                        self.data = data
                        self.headers = headers

                mock_request = MockRequest(
                    data=task_data,
                    headers={}
                )

                # Make API call
                logger.info(f"Creating task: {task_type}")
                response = api.post(mock_request)
                
                if response.status_code == status.HTTP_201_CREATED:
                    logger.info(f"Successfully created task: {task_type}")
                    created_tasks.append(task_type)
                else:
                    logger.error(f"Failed to create task: {task_type}")
                    failed_tasks.append(task_type)

        # Prepare response message
        logger.info(f"Task creation completed. Created: {created_tasks}, Failed: {failed_tasks}")
        if created_tasks:
            success_message = f"""
            Task Creation Results:
            
            Successfully Created Tasks:
            - {', '.join(created_tasks)}
            """
            if failed_tasks:
                success_message += f"\nFailed Tasks:\n- {', '.join(failed_tasks)}"
        else:
            success_message = "No tasks were created successfully."

        return render(request, self.template_name, {
            'success_message': success_message
        })

class CreateAzureTaskAPIView(APIView):
    def post(self, request):
        logger.info(f"Received request to create Azure task. Data: {request.data}")
        
        serializer = AzureTaskSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation failed. Errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        logger.info(f"Data validated successfully: {data}")
        
        # Prepare Azure DevOps API request
        azure_url = f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/{settings.AZURE_DEVOPS_PROJECT}/_apis/wit/workitems/$Task?api-version={settings.AZURE_DEVOPS_API_VERSION}"
        
        # Get PAT from settings
        pat = settings.AZURE_DEVOPS_PAT
        
        # Create Basic Auth header
        auth = base64.b64encode(f":{pat}".encode()).decode()
        
        # Prepare headers and request body
        body = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": data['title']
            },
            {
                "op": "add",
                "path": "/fields/System.Description",
                "value": data['description']
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.Activity",
                "value": data['activity']
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate",
                "value": data['original_estimate']
            },
            {
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork",
                "value": data['remaining_work']
            },
            {
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": data['assigned_to']
            },
            {
                "op": "add",
                "path": "/fields/System.IterationPath",
                "value": data['iteration_path']
            },
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": f"https://dev.azure.com/{settings.AZURE_DEVOPS_ORG}/_apis/wit/workitems/{data['user_story_id']}",
                    "attributes": {}
                }
            }
        ]
        
        # Calculate content length
        content_length = len(json.dumps(body))
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json-patch+json',
            'Accept': 'application/json',
            'Authorization': f'Basic {auth}',
            'Host': 'dev.azure.com',
            'Content-Length': str(content_length)
        }
        
        try:
            # Log curl command
            curl_command = f"""
            curl -X POST '{azure_url}' \\
            -H 'Content-Type: application/json-patch+json' \\
            -H 'Accept: application/json' \\
            -H 'Authorization: Basic {auth}' \\
            -H 'Host: dev.azure.com' \\
            -H 'Content-Length: {content_length}' \\
            -d '{json.dumps(body)}'
            """
            logger.info("Equivalent curl command:")
            logger.info(curl_command)
            
            logger.info(f"Sending request to Azure DevOps API. URL: {azure_url}")
            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Request body: {json.dumps(body, indent=2)}")
            
            response = requests.post(azure_url, headers=headers, json=body)
            logger.info(f"Azure DevOps API response status: {response.status_code}")
            
            try:
                response_data = response.json()
                formatted_response = json.dumps(response_data, indent=2)
                logger.info("Azure DevOps API Response:")
                logger.info(formatted_response)
                
                if response.status_code >= 400:
                    error_msg = response_data.get('message', 'Unknown error')
                    logger.error(f"Azure DevOps API error: {error_msg}")
                    return Response(
                        {"error": f"Azure DevOps API error: {error_msg}"}, 
                        status=response.status_code
                    )
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except ValueError:
                logger.error("Failed to parse JSON response")
                logger.info(f"Raw response: {response.text}")
                return Response(
                    {"error": "Invalid response from Azure DevOps API"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Request failed: {error_msg}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
                    error_msg = error_details.get('message', error_msg)
                except ValueError:
                    logger.error(f"Raw error response: {e.response.text}")
            
            return Response(
                {"error": f"Azure DevOps API error: {error_msg}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
