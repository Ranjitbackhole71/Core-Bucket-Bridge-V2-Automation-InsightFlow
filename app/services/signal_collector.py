"""
CORRECTED Signal Collector - SUPPORTING SIGNALS ONLY
NO SCORING AUTHORITY - Signals support Assignment Authority decisions only

This replaces evaluation_engine.py and scoring_engine.py as primary authorities
"""
from typing import Dict, Any, Optional
import logging

from .intent_extractor import IntentExtractor
from .repository_analyzer import RepositoryAnalyzer
from .feature_matcher import FeatureMatcher
from .pdf_analyzer import PDFAnalyzer
from .title_analyzer import TitleAnalyzer
from .description_analyzer import DescriptionAnalyzer

logger = logging.getLogger("signal_collector")

class SignalCollector:
    """
    SUPPORTING SIGNALS ONLY - NO SCORING AUTHORITY
    
    Collects technical signals to support Assignment Authority decisions.
    CANNOT determine final scores or classifications.
    """
    
    def __init__(self):
        self.intent_extractor = IntentExtractor()
        self.repository_analyzer = RepositoryAnalyzer()
        self.feature_matcher = FeatureMatcher()
        self.pdf_analyzer = PDFAnalyzer()
        self.title_analyzer = TitleAnalyzer()
        self.description_analyzer = DescriptionAnalyzer()
        
        # AUTHORITY RESTRICTION
        self.authority_level = "SUPPORTING_ONLY"
        self.can_determine_final_score = False
        self.can_override_assignment = False
    
    def collect_supporting_signals(
        self, 
        task_title: str, 
        task_description: str, 
        repository_url: Optional[str] = None,
        pdf_text: str = ""
    ) -> Dict[str, Any]:
        """
        Collect supporting signals for Assignment Authority evaluation
        
        IMPORTANT: This method DOES NOT determine final scores or classifications.
        It only provides technical signals for Assignment Authority to consider.
        
        Returns:nt
            Supporting signals dictionary (NOT evaluation result)
        """
        logger.info(f"[SIGNAL COLLECTOR] Collecting supporting signals for: {task_title[:50]}...")
        logger.warning("[SIGNAL COLLECTOR] NO SCORING AUTHORITY - Signals only")
        
        # Step 1: Extract Requirements Intent
        intent = self.intent_extractor.extract(task_title, task_description, pdf_text)
        logger.info(f"[SIGNAL COLLECTOR] Extracted {len(intent.get('expected_features', []))} expected features")
        
        # Step 2: Analyze Repository (if available)
        repo_signals = self.repository_analyzer.analyze(repository_url) if repository_url else {}

        # FIX: handle None safely
        if repo_signals is None:
            logger.warning("[SIGNAL COLLECTOR] repo_signals is None — analyzer failed")
            repo_signals = {}

        repo_available = bool(
            repo_signals and
            not repo_signals.get('error') and
            repo_signals.get('structure', {}).get('total_files', 0) > 0
        )
        logger.info(f"[SIGNAL COLLECTOR] Repository available: {repo_available}")
        
        # Step 3: Match Requirements to Implementation
        match_results = self.feature_matcher.compute_match(intent, repo_signals or {})
        logger.info(f"[SIGNAL COLLECTOR] Feature match ratio: {match_results.get('feature_match_ratio', 0)}")
        
        # Step 4: Analyze Individual Components
        title_signals = self.title_analyzer.analyze(task_title, task_description)
        desc_signals = self.description_analyzer.analyze(task_description)
        pdf_signals = self.pdf_analyzer.analyze_content(pdf_text)
        
        # Step 5: Package SUPPORTING SIGNALS (NO SCORING)
        supporting_signals = {
            # SIGNAL METADATA
            "signal_authority": "SUPPORTING_ONLY",
            "can_determine_score": False,
            "signal_collection_complete": True,
            
            # REQUIREMENT SIGNALS
            "intent_signals": intent,
            "expected_features": intent.get('expected_features', []),
            "expected_complexity": intent.get('expected_complexity', 'medium'),
            "technical_requirements": intent.get('technical_requirements', []),
            
            # IMPLEMENTATION SIGNALS
            "repository_available": repo_available,
            "repository_signals": repo_signals,
            "implementation_files": repo_signals.get('structure', {}).get('total_files', 0),
            "architecture_signals": repo_signals.get('architecture', {}),
            "quality_signals": repo_signals.get('quality', {}),
            
            # MATCHING SIGNALS
            "feature_match_ratio": match_results.get('feature_match_ratio', 0.0),
            "tech_stack_match": match_results.get('tech_stack_match', 0.0),
            "architecture_match": match_results.get('architecture_match', 0.0),
            "missing_features": match_results.get('missing_features', []),
            "implemented_features": match_results.get('implemented_features', []),
            
            # COMPONENT SIGNALS
            "title_signals": {
                "technical_keywords": title_signals.get('signals', {}).get('technical_keywords', []),
                "clarity_indicators": title_signals.get('signals', {}).get('clarity_score', 0),
                "domain_relevance": title_signals.get('signals', {}).get('domain_relevance', 0)
            },
            "description_signals": {
                "technical_density": desc_signals.get('metrics', {}).get('technical_term_ratio', 0),
                "content_depth": desc_signals.get('metrics', {}).get('content_depth', 0),
                "structure_quality": desc_signals.get('metrics', {}).get('structure_score', 0)
            },
            "pdf_signals": pdf_signals,
            
            # FAILURE INDICATORS (for Assignment Authority)
            "failure_indicators": self._extract_failure_indicators(
                repo_available, repo_signals, match_results, intent
            ),
            
            # EVIDENCE FOR ASSIGNMENT AUTHORITY
            "expected_vs_delivered_evidence": self._calculate_delivery_evidence(
                intent, match_results, repo_signals
            )
        }
        
        logger.info(f"[SIGNAL COLLECTOR] Signal collection complete - Repository: {repo_available}, Features: {len(intent.get('expected_features', []))}")
        return supporting_signals
    
    def _extract_failure_indicators(
        self, 
        repo_available: bool, 
        repo_signals: Dict[str, Any], 
        match_results: Dict[str, Any],
        intent: Dict[str, Any]
    ) -> list:
        """Extract failure indicators for Assignment Authority"""
        indicators = []
        
        if not repo_available:
            indicators.append("repository_not_found")
        
        if repo_signals.get('error'):
            indicators.append(f"repository_error: {repo_signals['error']}")
        
        missing_features = match_results.get('missing_features', [])
        if len(missing_features) > 0:
            indicators.append(f"missing_features_count: {len(missing_features)}")
        
        if match_results.get('feature_match_ratio', 0) < 0.3:
            indicators.append("low_feature_match_ratio")
        
        expected_complexity = intent.get('expected_complexity', 'medium')
        file_count = repo_signals.get('structure', {}).get('total_files', 0)
        complexity_thresholds = {"low": 3, "medium": 8, "high": 20}
        if file_count < complexity_thresholds.get(expected_complexity, 8) * 0.5:
            indicators.append("insufficient_implementation_scope")
        
        return indicators
    
    def _calculate_delivery_evidence(
        self, 
        intent: Dict[str, Any], 
        match_results: Dict[str, Any],
        repo_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate expected vs delivered evidence for Assignment Authority"""
        expected_features = intent.get('expected_features', [])
        implemented_features = match_results.get('implemented_features', [])
        missing_features = match_results.get('missing_features', [])
        
        expected_count = len(expected_features)
        delivered_count = len(implemented_features)
        missing_count = len(missing_features)
        
        return {
            "expected_count": expected_count,
            "delivered_count": delivered_count,
            "missing_count": missing_count,
            "delivery_ratio": delivered_count / expected_count if expected_count > 0 else 0.0,
            "completion_percentage": (delivered_count / expected_count * 100) if expected_count > 0 else 0.0,
            "gap_analysis": {
                "critical_gaps": [f for f in missing_features if 'critical' in str(f).lower()],
                "major_gaps": [f for f in missing_features if 'major' in str(f).lower()],
                "minor_gaps": [f for f in missing_features if f not in [g for g in missing_features if 'critical' in str(f).lower() or 'major' in str(f).lower()]]
            }
        }
    
    def get_signal_summary(self, signals: Dict[str, Any]) -> str:
        """Generate summary of collected signals (NOT evaluation summary)"""
        repo_status = "available" if signals.get("repository_available") else "not found"
        feature_count = len(signals.get("expected_features", []))
        match_ratio = signals.get("feature_match_ratio", 0)
        
        return (
            f"Signal Collection Summary: Repository {repo_status}, "
            f"{feature_count} expected features, "
            f"{match_ratio:.1%} feature match ratio. "
            "Signals ready for Assignment Authority evaluation."
        )

# Global signal collector instance
signal_collector = SignalCollector()