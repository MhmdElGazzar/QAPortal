# QA Portal Requirements

## Overview
A portal for QA services with integration to Azure DevOps.

## Tech Stack
- Django REST API backend
- React frontend

## Service 1: Create Tasks on Azure DevOps User Stories

### Inputs
- Authentication:
  - Azure DevOps organization name (ThiqahDev)
  - Project name (SFDA.Faseh)
- User story ID
- List of tasks to be created:
  - Design
  - Review
  - Execute
  - Retest

### API Endpoint
POST request to Azure DevOps REST API:
`https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$Task?api-version=7.1-preview.3`

### Response
- Success (200): Full JSON response from Azure DevOps
- Error: JSON with "error" and "details" keys

### Example Request Format
```json
[
    {
        "op": "add",
        "path": "/fields/System.Title",
        "value": "QC_Review user story"
    },
    {
        "op": "add",
        "path": "/fields/System.Description",
        "value": "Task description"
    },
    {
        "op": "add",
        "path": "/fields/Microsoft.VSTS.Common.Activity",
        "value": "Testing"
    },
    {
        "op": "add",
        "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate",
        "value": 2
    },
    {
        "op": "add",
        "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork",
        "value": 1
    },
    {
        "op": "add",
        "path": "/fields/System.AssignedTo",
        "value": "user@example.com"
    },
    {
        "op": "add",
        "path": "/fields/System.IterationPath",
        "value": "Project\\Sprint"
    },
    {
        "op": "add",
        "path": "/relations/-",
        "value": {
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": "https://dev.azure.com/org/_apis/wit/workitems/{{us_id}}",
            "attributes": {}
        }
    }
]
