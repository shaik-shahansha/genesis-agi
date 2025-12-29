"""
Cognitive Decision Framework - Intelligent Reasoning for Autonomous Actions

This module provides the "thinking layer" between wanting to do something
and actually doing it. It adds:

1. Risk Assessment - Evaluate potential consequences
2. Decision Trees - Break complex decisions into steps
3. Confidence Calculation - How sure are we about this action?
4. Alternative Generation - Consider multiple approaches
5. Outcome Prediction - What will likely happen?
6. Learning Loop - Improve decisions based on past results

This is what makes a Mind truly intelligent, not just reactive.

Example:
    # Mind evaluates whether to send an email
    decision = await mind.cognitive.evaluate_action(
        action="send_email",
        context="User asked me to contact their boss",
        parameters={"to": "boss@company.com", "urgent": True}
    )
    
    if decision.should_proceed:
        # Take action
        await mind.action_executor.request_action(...)
    else:
        # Explain why not
        return decision.reasoning
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    NONE = "none"  # No risk
    LOW = "low"  # Minimal risk
    MEDIUM = "medium"  # Moderate risk
    HIGH = "high"  # Significant risk
    CRITICAL = "critical"  # Dangerous


class DecisionConfidence(str, Enum):
    """Confidence in a decision."""
    VERY_LOW = "very_low"  # < 30%
    LOW = "low"  # 30-50%
    MODERATE = "moderate"  # 50-70%
    HIGH = "high"  # 70-90%
    VERY_HIGH = "very_high"  # > 90%


@dataclass
class ActionEvaluation:
    """Evaluation of a potential action."""
    action_name: str
    should_proceed: bool
    confidence: DecisionConfidence
    confidence_score: float  # 0-1
    risk_level: RiskLevel
    risk_score: float  # 0-1
    
    # Reasoning
    reasoning: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    
    # Predictions
    predicted_outcome: str = ""
    success_probability: float = 0.5
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionRecord:
    """Record of a decision and its actual outcome."""
    decision_id: str
    action_name: str
    evaluation: ActionEvaluation
    was_executed: bool
    actual_outcome: Optional[str] = None
    outcome_matched_prediction: Optional[bool] = None
    lessons_learned: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class CognitiveFramework:
    """
    Intelligent decision-making system for autonomous Minds.
    
    Provides reasoning, risk assessment, and learning capabilities
    to make Minds truly intelligent rather than just reactive.
    """
    
    def __init__(self, mind):
        """Initialize cognitive framework.
        
        Args:
            mind: The Mind instance this framework belongs to
        """
        self.mind = mind
        
        # Decision history for learning
        self.decision_history: List[DecisionRecord] = []
        
        # Learned patterns
        self.risk_patterns: Dict[str, float] = {}  # action -> historical risk
        self.success_patterns: Dict[str, float] = {}  # action -> success rate
        self.failure_patterns: Dict[str, List[str]] = {}  # action -> common failures
        
        # Configuration
        self.risk_tolerance = 0.5  # 0=very cautious, 1=risk-taking
        self.min_confidence_to_act = 0.6  # Minimum confidence to proceed
    
    async def evaluate_action(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        context: str = "",
        user_request: bool = False
    ) -> ActionEvaluation:
        """Evaluate whether to take an action.
        
        Args:
            action_name: Name of action to evaluate
            parameters: Action parameters
            context: Context for the action
            user_request: Whether this was explicitly requested by user
            
        Returns:
            ActionEvaluation with decision
        """
        # Get action definition
        if not hasattr(self.mind, 'action_executor'):
            return self._create_rejection("Action executor not available")
        
        action_def = self.mind.action_executor.actions.get(action_name)
        if not action_def:
            return self._create_rejection(f"Unknown action: {action_name}")
        
        # Calculate risk score
        risk_level, risk_score = self._assess_risk(action_def, parameters, context)
        
        # Generate reasoning using LLM
        reasoning_prompt = self._build_reasoning_prompt(
            action_def, parameters, context, risk_level, user_request
        )
        
        reasoning = await self.mind.think(
            reasoning_prompt,
            context="action_evaluation"
        )
        
        # Parse reasoning (simplified - in production would use structured output)
        should_proceed = self._parse_decision(reasoning, user_request, risk_score)
        pros, cons, alternatives = self._parse_reasoning(reasoning)
        
        # Calculate confidence
        confidence_score = self._calculate_confidence(
            action_name, parameters, context, user_request, risk_score
        )
        confidence = self._score_to_confidence(confidence_score)
        
        # Predict outcome
        predicted_outcome, success_prob = self._predict_outcome(
            action_name, parameters, reasoning
        )
        
        # Create evaluation
        evaluation = ActionEvaluation(
            action_name=action_name,
            should_proceed=should_proceed,
            confidence=confidence,
            confidence_score=confidence_score,
            risk_level=risk_level,
            risk_score=risk_score,
            reasoning=reasoning,
            pros=pros,
            cons=cons,
            alternatives=alternatives,
            predicted_outcome=predicted_outcome,
            success_probability=success_prob,
            context={
                "user_request": user_request,
                "context": context,
                "parameters": parameters
            }
        )
        
        return evaluation
    
    def _assess_risk(
        self,
        action_def,
        parameters: Dict[str, Any],
        context: str
    ) -> Tuple[RiskLevel, float]:
        """Assess risk level of an action.
        
        Returns:
            Tuple of (risk_level, risk_score)
        """
        # Start with action's base risk
        risk_score = action_def.risk_level
        
        # Adjust based on historical data
        if action_def.name in self.risk_patterns:
            historical_risk = self.risk_patterns[action_def.name]
            risk_score = (risk_score + historical_risk) / 2
        
        # Increase risk for certain parameters
        if "delete" in str(parameters).lower():
            risk_score += 0.2
        if "permanent" in str(parameters).lower():
            risk_score += 0.2
        if "public" in str(parameters).lower():
            risk_score += 0.1
        
        # Check permission level
        from genesis.core.autonomy import PermissionLevel
        if action_def.permission_level == PermissionLevel.ABSOLUTELY_FORBIDDEN:
            risk_score = 1.0
        elif action_def.permission_level == PermissionLevel.REQUIRES_CONFIRMATION:
            risk_score = max(0.5, risk_score)
        
        risk_score = min(1.0, risk_score)
        
        # Map to risk level
        if risk_score < 0.2:
            risk_level = RiskLevel.NONE
        elif risk_score < 0.4:
            risk_level = RiskLevel.LOW
        elif risk_score < 0.6:
            risk_level = RiskLevel.MEDIUM
        elif risk_score < 0.8:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        return risk_level, risk_score
    
    def _build_reasoning_prompt(
        self,
        action_def,
        parameters: Dict[str, Any],
        context: str,
        risk_level: RiskLevel,
        user_request: bool
    ) -> str:
        """Build prompt for LLM to reason about action."""
        prompt = f"""I'm considering taking this action:

ACTION: {action_def.name}
DESCRIPTION: {action_def.description}
PARAMETERS: {json.dumps(parameters, indent=2)}
CONTEXT: {context}
RISK LEVEL: {risk_level.value}
USER REQUESTED: {user_request}

I need to decide whether to proceed. Consider:

1. BENEFITS: What positive outcomes could result?
2. RISKS: What could go wrong?
3. ALTERNATIVES: Are there better approaches?
4. TIMING: Is now the right time?
5. ALIGNMENT: Does this align with my goals and values?

Historical data:
- Times I've done this before: {self._get_action_count(action_def.name)}
- Previous success rate: {self._get_success_rate(action_def.name):.0%}

Provide a thoughtful analysis and recommend whether to proceed.
"""
        return prompt
    
    def _parse_decision(
        self,
        reasoning: str,
        user_request: bool,
        risk_score: float
    ) -> bool:
        """Parse LLM reasoning to extract decision."""
        reasoning_lower = reasoning.lower()
        
        # User requests get higher preference
        if user_request:
            # Only reject if explicitly dangerous or LLM says no
            if "do not proceed" in reasoning_lower or "should not" in reasoning_lower:
                if risk_score > 0.7:  # High risk and LLM says no
                    return False
                return True  # User requested, moderate risk, proceed
            return True
        
        # Autonomous actions require clear recommendation
        positive_indicators = [
            "recommend proceeding", "should proceed", "go ahead",
            "safe to", "good idea", "proceed", "yes"
        ]
        negative_indicators = [
            "do not proceed", "should not", "don't recommend",
            "too risky", "not advisable", "no"
        ]
        
        positive_count = sum(1 for ind in positive_indicators if ind in reasoning_lower)
        negative_count = sum(1 for ind in negative_indicators if ind in reasoning_lower)
        
        if negative_count > positive_count:
            return False
        if positive_count > 0:
            return True
        
        # Default: proceed if risk is acceptable
        return risk_score <= self.risk_tolerance
    
    def _parse_reasoning(self, reasoning: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract pros, cons, and alternatives from reasoning."""
        pros = []
        cons = []
        alternatives = []
        
        # Simple parsing (in production would use better NLP)
        lines = reasoning.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['benefit', 'pro', 'advantage', 'positive']):
                pros.append(line.strip())
            elif any(word in line_lower for word in ['risk', 'con', 'disadvantage', 'negative']):
                cons.append(line.strip())
            elif any(word in line_lower for word in ['alternative', 'instead', 'could also']):
                alternatives.append(line.strip())
        
        return pros[:3], cons[:3], alternatives[:2]
    
    def _calculate_confidence(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        context: str,
        user_request: bool,
        risk_score: float
    ) -> float:
        """Calculate confidence in decision."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if user requested
        if user_request:
            confidence += 0.3
        
        # Higher confidence if we've done this before successfully
        if action_name in self.success_patterns:
            success_rate = self.success_patterns[action_name]
            confidence += (success_rate - 0.5) * 0.4  # -0.2 to +0.2
        
        # Lower confidence for high-risk actions
        confidence -= risk_score * 0.2
        
        # Higher confidence if context is clear
        if len(context) > 50:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _score_to_confidence(self, score: float) -> DecisionConfidence:
        """Convert confidence score to enum."""
        if score < 0.3:
            return DecisionConfidence.VERY_LOW
        elif score < 0.5:
            return DecisionConfidence.LOW
        elif score < 0.7:
            return DecisionConfidence.MODERATE
        elif score < 0.9:
            return DecisionConfidence.HIGH
        else:
            return DecisionConfidence.VERY_HIGH
    
    def _predict_outcome(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        reasoning: str
    ) -> Tuple[str, float]:
        """Predict the outcome of an action."""
        # Extract prediction from reasoning (simplified)
        prediction = "Action will likely succeed"
        success_prob = 0.7
        
        # Adjust based on history
        if action_name in self.success_patterns:
            success_prob = self.success_patterns[action_name]
        
        # Look for outcome predictions in reasoning
        reasoning_lower = reasoning.lower()
        if "likely to succeed" in reasoning_lower or "should work" in reasoning_lower:
            success_prob = min(1.0, success_prob + 0.1)
        elif "might fail" in reasoning_lower or "uncertain" in reasoning_lower:
            success_prob = max(0.0, success_prob - 0.2)
        
        return prediction, success_prob
    
    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        success: bool
    ):
        """Record the actual outcome of a decision for learning.
        
        Args:
            decision_id: ID of the decision
            actual_outcome: What actually happened
            success: Whether the action succeeded
        """
        # Find the decision record
        for record in self.decision_history:
            if record.decision_id == decision_id:
                record.actual_outcome = actual_outcome
                record.outcome_matched_prediction = success == (
                    record.evaluation.success_probability > 0.5
                )
                
                # Learn from this outcome
                self._learn_from_outcome(record, success)
                break
    
    def _learn_from_outcome(self, record: DecisionRecord, success: bool):
        """Update learned patterns based on outcome."""
        action_name = record.action_name
        
        # Update success patterns
        if action_name not in self.success_patterns:
            self.success_patterns[action_name] = 0.5
        
        # Exponential moving average
        alpha = 0.3  # Learning rate
        current_success_rate = self.success_patterns[action_name]
        new_success_rate = (alpha * (1.0 if success else 0.0)) + ((1 - alpha) * current_success_rate)
        self.success_patterns[action_name] = new_success_rate
        
        # Update risk patterns
        if not success:
            # This action turned out riskier than expected
            if action_name not in self.risk_patterns:
                self.risk_patterns[action_name] = record.evaluation.risk_score
            self.risk_patterns[action_name] = min(
                1.0,
                self.risk_patterns[action_name] + 0.1
            )
            
            # Record failure pattern
            if action_name not in self.failure_patterns:
                self.failure_patterns[action_name] = []
            self.failure_patterns[action_name].append(record.actual_outcome)
    
    def _get_action_count(self, action_name: str) -> int:
        """Get number of times this action was taken."""
        return sum(
            1 for record in self.decision_history
            if record.action_name == action_name and record.was_executed
        )
    
    def _get_success_rate(self, action_name: str) -> float:
        """Get historical success rate for action."""
        return self.success_patterns.get(action_name, 0.5)
    
    def _create_rejection(self, reason: str) -> ActionEvaluation:
        """Create a rejection evaluation."""
        return ActionEvaluation(
            action_name="unknown",
            should_proceed=False,
            confidence=DecisionConfidence.VERY_HIGH,
            confidence_score=0.95,
            risk_level=RiskLevel.CRITICAL,
            risk_score=1.0,
            reasoning=reason,
            cons=[reason]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cognitive framework statistics."""
        total_decisions = len(self.decision_history)
        executed = sum(1 for d in self.decision_history if d.was_executed)
        
        return {
            "total_decisions": total_decisions,
            "actions_taken": executed,
            "actions_rejected": total_decisions - executed,
            "learned_patterns": len(self.success_patterns),
            "risk_patterns": len(self.risk_patterns),
            "average_confidence": self._calculate_average_confidence()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across decisions."""
        if not self.decision_history:
            return 0.0
        total = sum(d.evaluation.confidence_score for d in self.decision_history)
        return total / len(self.decision_history)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "risk_tolerance": self.risk_tolerance,
            "min_confidence_to_act": self.min_confidence_to_act,
            "success_patterns": self.success_patterns,
            "risk_patterns": self.risk_patterns,
            "failure_patterns": self.failure_patterns,
            "decision_count": len(self.decision_history)
        }
    
    @classmethod
    def from_dict(cls, mind, data: Dict[str, Any]) -> 'CognitiveFramework':
        """Deserialize from dictionary."""
        framework = cls(mind)
        framework.risk_tolerance = data.get("risk_tolerance", 0.5)
        framework.min_confidence_to_act = data.get("min_confidence_to_act", 0.6)
        framework.success_patterns = data.get("success_patterns", {})
        framework.risk_patterns = data.get("risk_patterns", {})
        framework.failure_patterns = data.get("failure_patterns", {})
        return framework
