"""
Kenny Systems Integration for Graph Intelligence

Integrates the FastToG reasoning engine with Kenny's existing automation systems,
providing a bridge between graph-based reasoning and actual UI automation.
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import json
import os

from .fastog_reasoning import FastToGReasoningEngine, ReasoningRequest, ReasoningMode, FastToGResult
from .schema_manager import SchemaManager
from .data_ingestion import DataIngestionPipeline, IngestionResult

logger = logging.getLogger(__name__)


class AutomationStatus(Enum):
    """Status of automation execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AutomationTask:
    """Represents an automation task enhanced with graph intelligence."""
    task_id: str
    user_intent: str
    application: str
    context: Dict[str, Any]
    reasoning_result: Optional[FastToGResult] = None
    execution_plan: List[Dict[str, Any]] = None
    status: AutomationStatus = AutomationStatus.PENDING
    start_time: float = 0.0
    completion_time: float = 0.0
    success_rate: float = 0.0
    error_messages: List[str] = None
    
    def __post_init__(self):
        if self.execution_plan is None:
            self.execution_plan = []
        if self.error_messages is None:
            self.error_messages = []


@dataclass
class IntegrationMetrics:
    """Metrics for Kenny-FastToG integration performance."""
    reasoning_time: float
    action_generation_time: float
    total_integration_time: float
    communities_used: int
    actions_generated: int
    automation_success_rate: float
    confidence_score: float


class KennyAutomationBridge:
    """Bridge between FastToG reasoning and Kenny's automation systems."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.fastog_engine = FastToGReasoningEngine(schema_manager)
        self.data_pipeline = DataIngestionPipeline(schema_manager)
        
        # Integration state
        self.active_tasks: Dict[str, AutomationTask] = {}
        self.automation_callbacks: Dict[str, Callable] = {}
        
        # Performance tracking
        self.integration_metrics: List[IntegrationMetrics] = []
        
    async def execute_intelligent_automation(self, user_intent: str, 
                                           context: Dict[str, Any],
                                           reasoning_mode: ReasoningMode = ReasoningMode.COMMUNITY_BASED,
                                           max_communities: int = 8) -> AutomationTask:
        """
        Execute automation with graph intelligence reasoning.
        
        Args:
            user_intent: What the user wants to accomplish
            context: Current application/UI context
            reasoning_mode: Which reasoning approach to use
            max_communities: Maximum communities to analyze
            
        Returns:
            AutomationTask with reasoning results and execution plan
        """
        start_time = time.time()
        task_id = f"task_{int(start_time)}_{id(user_intent) % 10000}"
        
        logger.info(f"🚀 Starting intelligent automation: {user_intent}")
        
        # Create automation task
        task = AutomationTask(
            task_id=task_id,
            user_intent=user_intent,
            application=context.get('application', 'unknown'),
            context=context,
            start_time=start_time
        )
        
        self.active_tasks[task_id] = task
        
        try:
            # Phase 1: FastToG Reasoning
            reasoning_start = time.time()
            reasoning_request = ReasoningRequest(
                user_intent=user_intent,
                context=context,
                max_communities=max_communities,
                reasoning_mode=reasoning_mode,
                include_explanations=True
            )
            
            reasoning_result = await self.fastog_engine.reason(reasoning_request)
            task.reasoning_result = reasoning_result
            reasoning_time = time.time() - reasoning_start
            
            # Phase 2: Convert reasoning to execution plan
            plan_start = time.time()
            execution_plan = self._convert_reasoning_to_plan(reasoning_result, context)
            task.execution_plan = execution_plan
            plan_time = time.time() - plan_start
            
            # Phase 3: Update task status
            task.status = AutomationStatus.IN_PROGRESS
            total_time = time.time() - start_time
            
            # Record integration metrics
            metrics = IntegrationMetrics(
                reasoning_time=reasoning_time,
                action_generation_time=plan_time,
                total_integration_time=total_time,
                communities_used=reasoning_result.communities_analyzed,
                actions_generated=len(execution_plan),
                automation_success_rate=0.0,  # Will be updated after execution
                confidence_score=reasoning_result.overall_confidence
            )
            self.integration_metrics.append(metrics)
            
            logger.info(f"✅ Intelligent automation prepared: {len(execution_plan)} steps planned "
                       f"({reasoning_result.communities_analyzed} communities, "
                       f"{reasoning_result.overall_confidence:.1%} confidence)")
            
            return task
            
        except Exception as e:
            logger.error(f"❌ Intelligent automation failed: {e}")
            task.status = AutomationStatus.FAILED
            task.error_messages.append(str(e))
            return task
    
    def _convert_reasoning_to_plan(self, reasoning_result: FastToGResult, 
                                 context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert FastToG reasoning result to Kenny execution plan."""
        execution_plan = []
        
        if not reasoning_result.final_recommendation:
            return execution_plan
        
        recommended_actions = reasoning_result.final_recommendation.get('recommended_actions', [])
        
        for i, action in enumerate(recommended_actions):
            # Convert graph actions to Kenny automation steps
            step = self._convert_action_to_kenny_step(action, i + 1, context)
            if step:
                execution_plan.append(step)
        
        # Add validation steps
        if execution_plan:
            execution_plan.append({
                'step_number': len(execution_plan) + 1,
                'step_type': 'validate',
                'action': 'verify_task_completion',
                'parameters': {
                    'expected_outcome': context.get('expected_outcome', 'task completed'),
                    'validation_timeout': 5.0
                },
                'confidence': 0.8,
                'reasoning': 'Verify that the automation achieved the intended result'
            })
        
        return execution_plan
    
    def _convert_action_to_kenny_step(self, action: Dict[str, Any], step_number: int,
                                    context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single action to a Kenny automation step."""
        action_type = action.get('type', '')
        
        if action_type == 'click':
            return {
                'step_number': step_number,
                'step_type': 'ui_interaction',
                'action': 'click',
                'parameters': {
                    'target_element': action.get('element_text', ''),
                    'coordinates': action.get('coordinates', []),
                    'target_id': action.get('target', ''),
                    'click_type': 'left',
                    'wait_after': 1.0
                },
                'confidence': action.get('confidence', 0.7),
                'reasoning': action.get('reasoning', 'Click UI element'),
                'fallback_strategies': [
                    {'method': 'coordinate_click', 'coordinates': action.get('coordinates', [])},
                    {'method': 'text_search', 'text': action.get('element_text', '')}
                ]
            }
        
        elif action_type == 'input':
            return {
                'step_number': step_number,
                'step_type': 'ui_interaction',
                'action': 'type_text',
                'parameters': {
                    'target_element': action.get('element_text', ''),
                    'coordinates': action.get('coordinates', []),
                    'text_to_type': context.get('input_text', ''),
                    'clear_first': True,
                    'wait_after': 0.5
                },
                'confidence': action.get('confidence', 0.7),
                'reasoning': action.get('reasoning', 'Input text into field'),
                'fallback_strategies': [
                    {'method': 'coordinate_click_then_type', 'coordinates': action.get('coordinates', [])}
                ]
            }
        
        elif action_type == 'navigate':
            return {
                'step_number': step_number,
                'step_type': 'ui_interaction',
                'action': 'navigate_menu',
                'parameters': {
                    'menu_item': action.get('element_text', ''),
                    'coordinates': action.get('coordinates', []),
                    'wait_for_menu': 2.0
                },
                'confidence': action.get('confidence', 0.7),
                'reasoning': action.get('reasoning', 'Navigate through menu'),
                'fallback_strategies': [
                    {'method': 'keyboard_shortcut', 'shortcut': self._infer_shortcut(action.get('element_text', ''))}
                ]
            }
        
        elif action_type == 'workflow':
            return {
                'step_number': step_number,
                'step_type': 'workflow_execution',
                'action': 'execute_workflow',
                'parameters': {
                    'workflow_id': action.get('target', ''),
                    'workflow_name': action.get('workflow_name', ''),
                    'context_variables': context
                },
                'confidence': action.get('confidence', 0.9),
                'reasoning': action.get('reasoning', 'Execute predefined workflow'),
                'fallback_strategies': [
                    {'method': 'step_by_step_execution'}
                ]
            }
        
        else:
            # Generic action
            return {
                'step_number': step_number,
                'step_type': 'generic',
                'action': action_type,
                'parameters': action,
                'confidence': action.get('confidence', 0.5),
                'reasoning': action.get('reasoning', f'Execute {action_type} action'),
                'fallback_strategies': []
            }
    
    def _infer_shortcut(self, element_text: str) -> str:
        """Infer keyboard shortcut for menu items."""
        shortcuts = {
            'save': 'ctrl+s',
            'open': 'ctrl+o', 
            'copy': 'ctrl+c',
            'paste': 'ctrl+v',
            'new': 'ctrl+n',
            'close': 'ctrl+w',
            'file': 'alt+f',
            'edit': 'alt+e',
            'help': 'f1'
        }
        
        text_lower = element_text.lower()
        for keyword, shortcut in shortcuts.items():
            if keyword in text_lower:
                return shortcut
        
        return ''  # No shortcut found
    
    async def execute_automation_plan(self, task_id: str) -> bool:
        """
        Execute the automation plan for a task.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Success status of execution
        """
        if task_id not in self.active_tasks:
            logger.error(f"Task {task_id} not found")
            return False
        
        task = self.active_tasks[task_id]
        
        if task.status != AutomationStatus.IN_PROGRESS:
            logger.error(f"Task {task_id} is not ready for execution (status: {task.status})")
            return False
        
        logger.info(f"🎯 Executing automation plan for: {task.user_intent}")
        
        try:
            success_count = 0
            
            for step in task.execution_plan:
                step_success = await self._execute_automation_step(step, task)
                
                if step_success:
                    success_count += 1
                    logger.info(f"✅ Step {step['step_number']}: {step['action']} completed")
                else:
                    logger.error(f"❌ Step {step['step_number']}: {step['action']} failed")
                    
                    # Try fallback strategies
                    if step.get('fallback_strategies'):
                        for fallback in step['fallback_strategies']:
                            logger.info(f"🔄 Trying fallback: {fallback['method']}")
                            fallback_success = await self._execute_fallback_strategy(fallback, step, task)
                            if fallback_success:
                                success_count += 1
                                logger.info(f"✅ Fallback succeeded for step {step['step_number']}")
                                break
                        else:
                            logger.error(f"❌ All fallbacks failed for step {step['step_number']}")
                
                # Brief pause between steps
                await asyncio.sleep(0.1)
            
            # Calculate success rate
            task.success_rate = success_count / len(task.execution_plan) if task.execution_plan else 0.0
            
            if task.success_rate >= 0.8:  # 80% success threshold
                task.status = AutomationStatus.COMPLETED
                task.completion_time = time.time()
                logger.info(f"🎉 Automation completed successfully: {task.success_rate:.1%} success rate")
                return True
            else:
                task.status = AutomationStatus.FAILED
                logger.error(f"❌ Automation failed: {task.success_rate:.1%} success rate")
                return False
                
        except Exception as e:
            logger.error(f"❌ Automation execution error: {e}")
            task.status = AutomationStatus.FAILED
            task.error_messages.append(str(e))
            return False
    
    async def _execute_automation_step(self, step: Dict[str, Any], task: AutomationTask) -> bool:
        """Execute a single automation step."""
        step_type = step.get('step_type', '')
        action = step.get('action', '')
        
        # Simulate step execution (in real implementation, would call Kenny's automation APIs)
        logger.debug(f"Executing {step_type}:{action} - {step.get('reasoning', '')}")
        
        # Simulate execution time
        await asyncio.sleep(0.05)
        
        # Simulate success based on confidence
        confidence = step.get('confidence', 0.5)
        success_probability = min(0.95, confidence + 0.1)  # Boost slightly, cap at 95%
        
        import random
        success = random.random() < success_probability
        
        if not success:
            error_msg = f"Step {step['step_number']} failed: {step.get('reasoning', 'Unknown error')}"
            task.error_messages.append(error_msg)
        
        return success
    
    async def _execute_fallback_strategy(self, fallback: Dict[str, Any], 
                                       original_step: Dict[str, Any],
                                       task: AutomationTask) -> bool:
        """Execute a fallback strategy for a failed step."""
        method = fallback.get('method', '')
        
        logger.debug(f"Executing fallback: {method}")
        
        # Simulate fallback execution
        await asyncio.sleep(0.1)
        
        # Fallbacks have lower success rate
        import random
        success = random.random() < 0.6
        
        return success
    
    def ingest_automation_feedback(self, task_id: str, 
                                 screen_data: Dict[str, Any],
                                 result_data: Dict[str, Any]) -> IngestionResult:
        """
        Ingest automation results back into the knowledge graph for learning.
        
        Args:
            task_id: ID of completed task
            screen_data: Screen capture and OCR data
            result_data: Automation results and success metrics
            
        Returns:
            IngestionResult from data pipeline
        """
        if task_id not in self.active_tasks:
            logger.error(f"Cannot ingest feedback for unknown task: {task_id}")
            return IngestionResult()
        
        task = self.active_tasks[task_id]
        
        # Prepare context for ingestion
        ingestion_context = {
            'task_id': task_id,
            'user_intent': task.user_intent,
            'application': task.application,
            'success_rate': task.success_rate,
            'communities_used': task.reasoning_result.communities_analyzed if task.reasoning_result else 0,
            'automation_result': result_data.get('success', False),
            'execution_time': task.completion_time - task.start_time if task.completion_time > 0 else 0
        }
        
        # Ingest OCR data if available
        ocr_data = screen_data.get('ocr_results', [])
        if ocr_data:
            result = self.data_pipeline.ingest_ocr_results(ocr_data, ingestion_context)
            
            # Create workflow data from successful automation
            if task.success_rate >= 0.8 and task.reasoning_result:
                workflow_data = {
                    'name': f"Automated: {task.user_intent}",
                    'description': f"Successfully automated task with {task.success_rate:.1%} success rate",
                    'steps': [step for step in task.execution_plan if step['step_type'] != 'validate'],
                    'status': 'completed',
                    'success_rate': task.success_rate,
                    'avg_duration': task.completion_time - task.start_time if task.completion_time > 0 else 0,
                    'execution_count': 1,
                    'complexity': 'simple' if len(task.execution_plan) <= 3 else 'medium',
                    'related_elements': []  # Would extract from successful steps
                }
                
                workflow_result = self.data_pipeline.ingest_workflow_data(workflow_data)
                result.nodes_created += workflow_result.nodes_created
                result.relationships_created += workflow_result.relationships_created
            
            logger.info(f"✅ Ingested automation feedback: {result.nodes_created} nodes, "
                       f"{result.relationships_created} relationships")
            
            return result
        
        return IngestionResult()
    
    def get_task_status(self, task_id: str) -> Optional[AutomationTask]:
        """Get the current status of an automation task."""
        return self.active_tasks.get(task_id)
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the Kenny-FastToG integration."""
        if not self.integration_metrics:
            return {
                'total_tasks': 0,
                'avg_reasoning_time': 0.0,
                'avg_confidence': 0.0,
                'avg_actions_per_task': 0.0
            }
        
        metrics = self.integration_metrics
        
        return {
            'total_tasks': len(metrics),
            'avg_reasoning_time': sum(m.reasoning_time for m in metrics) / len(metrics),
            'avg_action_generation_time': sum(m.action_generation_time for m in metrics) / len(metrics),
            'avg_total_integration_time': sum(m.total_integration_time for m in metrics) / len(metrics),
            'avg_communities_used': sum(m.communities_used for m in metrics) / len(metrics),
            'avg_actions_per_task': sum(m.actions_generated for m in metrics) / len(metrics),
            'avg_confidence': sum(m.confidence_score for m in metrics) / len(metrics),
            'completed_tasks': len([t for t in self.active_tasks.values() if t.status == AutomationStatus.COMPLETED]),
            'failed_tasks': len([t for t in self.active_tasks.values() if t.status == AutomationStatus.FAILED])
        }
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks to free memory."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        tasks_to_remove = []
        for task_id, task in self.active_tasks.items():
            if (task.status in [AutomationStatus.COMPLETED, AutomationStatus.FAILED] and
                task.start_time < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"🧹 Cleaned up {len(tasks_to_remove)} old automation tasks")


# Test the Kenny integration system
if __name__ == "__main__":
    print("🧪 Testing Kenny Integration System...")
    
    async def test_integration():
        with SchemaManager() as sm:
            integration = KennyAutomationBridge(sm)
            
            # Test intelligent automation
            context = {
                'application': 'notepad',
                'ui_elements': [
                    {'text': 'Save', 'type': 'button', 'coordinates': [200, 300]},
                    {'text': 'File', 'type': 'menu', 'coordinates': [50, 25]}
                ],
                'expected_outcome': 'document saved successfully',
                'input_text': 'test_document.txt'
            }
            
            task = await integration.execute_intelligent_automation(
                "save current document to file",
                context,
                ReasoningMode.COMMUNITY_BASED,
                max_communities=3
            )
            
            print(f"✅ Intelligent Automation Results:")
            print(f"   - Task ID: {task.task_id}")
            print(f"   - Status: {task.status.value}")
            print(f"   - Execution Plan: {len(task.execution_plan)} steps")
            
            if task.reasoning_result:
                print(f"   - Communities Analyzed: {task.reasoning_result.communities_analyzed}")
                print(f"   - Overall Confidence: {task.reasoning_result.overall_confidence:.1%}")
            
            # Test automation execution
            if task.execution_plan:
                print(f"   - Execution Plan Steps:")
                for step in task.execution_plan:
                    print(f"     {step['step_number']}. {step['action']}: {step['reasoning']}")
                
                # Execute the plan
                success = await integration.execute_automation_plan(task.task_id)
                print(f"✅ Automation Execution: {'SUCCESS' if success else 'FAILED'}")
                print(f"   - Success Rate: {task.success_rate:.1%}")
            
            # Test metrics
            metrics = integration.get_integration_metrics()
            print(f"✅ Integration Metrics:")
            print(f"   - Total Tasks: {metrics['total_tasks']}")
            print(f"   - Avg Reasoning Time: {metrics['avg_reasoning_time']:.3f}s")
            print(f"   - Avg Confidence: {metrics['avg_confidence']:.1%}")
            print(f"   - Avg Actions/Task: {metrics['avg_actions_per_task']:.1f}")
            
            return task
    
    # Run async test
    asyncio.run(test_integration())
    print("✅ Kenny Integration System testing completed!")