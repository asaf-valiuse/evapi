#!/usr/bin/env python3
"""
Deployment Safety Check Script
Ensures only one deployment workflow exists and validates configuration
"""
import os
import yaml
import glob
from pathlib import Path

def check_deployment_workflows():
    """Check for duplicate deployment workflows"""
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("✅ No workflows directory found")
        return True
    
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    deployment_workflows = []
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)
                
            # Check if this is a deployment workflow
            if content and 'jobs' in content:
                for job_name, job_config in content['jobs'].items():
                    if 'azure' in str(job_config).lower() or 'deploy' in str(job_config).lower():
                        deployment_workflows.append({
                            'file': workflow_file.name,
                            'job': job_name,
                            'triggers': content.get('on', {})
                        })
        except Exception as e:
            print(f"⚠️  Warning: Could not parse {workflow_file}: {e}")
    
    print(f"\n🔍 Deployment Workflows Found: {len(deployment_workflows)}")
    
    for workflow in deployment_workflows:
        print(f"  📋 {workflow['file']}")
        print(f"     Job: {workflow['job']}")
        print(f"     Triggers: {workflow['triggers']}")
    
    # Check for conflicts
    main_triggers = [w for w in deployment_workflows 
                    if w['triggers'].get('push', {}).get('branches', []) == ['main']]
    
    if len(main_triggers) > 1:
        print(f"\n❌ ERROR: {len(main_triggers)} workflows trigger on 'main' push!")
        print("   This will cause 409 deployment conflicts.")
        return False
    
    print(f"\n✅ Deployment configuration is safe")
    return True

def check_concurrency_control():
    """Check if workflows have concurrency control"""
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        return True
    
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    for workflow_file in workflow_files:
        try:
            with open(workflow_file, 'r') as f:
                content = yaml.safe_load(f)
                
            if content and 'concurrency' not in content:
                print(f"⚠️  Warning: {workflow_file.name} lacks concurrency control")
                return False
        except Exception:
            continue
    
    print("✅ All workflows have concurrency control")
    return True

if __name__ == "__main__":
    print("🛡️  DEPLOYMENT SAFETY CHECK")
    print("=" * 40)
    
    workflows_ok = check_deployment_workflows()
    concurrency_ok = check_concurrency_control()
    
    if workflows_ok and concurrency_ok:
        print(f"\n🎉 All deployment safety checks passed!")
        exit(0)
    else:
        print(f"\n❌ Deployment safety issues found!")
        exit(1)
