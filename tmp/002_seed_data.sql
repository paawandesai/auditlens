-- ============================================================================
-- AuditLens AI — Seed Data
-- ============================================================================
-- Framework signatures + regulatory map for EU AI Act Annex III Category 4
-- ============================================================================

-- ============================================================================
-- Framework Signatures (Python)
-- ============================================================================
INSERT INTO framework_signatures (name, ecosystem, category, hr_relevance_score, description, aliases, is_ai_framework) VALUES
-- Core ML
('scikit-learn', 'python', 'ml_classical', 0.70, 'Classical ML — common in candidate scoring', ARRAY['sklearn'], true),
('tensorflow', 'python', 'ml_deep_learning', 0.50, 'Deep learning — NLP for resume parsing', ARRAY['tf'], true),
('torch', 'python', 'ml_deep_learning', 0.50, 'PyTorch — deep learning framework', ARRAY['pytorch'], true),
('keras', 'python', 'ml_deep_learning', 0.50, 'High-level deep learning API', ARRAY[], true),
('xgboost', 'python', 'ml_classical', 0.70, 'Gradient boosting — tabular scoring', ARRAY[], true),
('lightgbm', 'python', 'ml_classical', 0.70, 'Fast gradient boosting', ARRAY[], true),
('catboost', 'python', 'ml_classical', 0.60, 'Gradient boosting with categorical support', ARRAY[], true),

-- NLP (high HR relevance)
('spacy', 'python', 'nlp', 0.80, 'NLP — resume parsing, entity extraction', ARRAY[], true),
('nltk', 'python', 'nlp', 0.60, 'Natural language toolkit', ARRAY[], true),
('transformers', 'python', 'nlp', 0.70, 'HuggingFace pretrained models', ARRAY[], true),
('sentence-transformers', 'python', 'nlp', 0.80, 'Sentence embeddings — candidate matching', ARRAY[], true),
('gensim', 'python', 'nlp', 0.60, 'Topic modeling and doc similarity', ARRAY[], true),
('flair', 'python', 'nlp', 0.60, 'Sequence labeling and text classification', ARRAY[], true),

-- LLM / GenAI
('openai', 'python', 'llm', 0.60, 'OpenAI API client', ARRAY[], true),
('anthropic', 'python', 'llm', 0.60, 'Anthropic Claude API client', ARRAY[], true),
('langchain', 'python', 'llm_orchestration', 0.60, 'LLM orchestration — chains, agents, RAG', ARRAY['langchain-core'], true),
('llama-index', 'python', 'llm_orchestration', 0.50, 'Data framework for LLM apps', ARRAY['llamaindex'], true),
('crewai', 'python', 'llm_agents', 0.50, 'Multi-agent AI framework', ARRAY[], true),
('autogen', 'python', 'llm_agents', 0.50, 'Microsoft multi-agent conversations', ARRAY[], true),

-- Computer Vision
('opencv-python', 'python', 'cv', 0.30, 'Computer vision — ID verification', ARRAY['cv2'], true),
('torchvision', 'python', 'cv', 0.30, 'PyTorch vision models', ARRAY[], true),
('ultralytics', 'python', 'cv', 0.20, 'YOLO object detection', ARRAY[], true),

-- Fairness / Bias (very high HR signal)
('fairlearn', 'python', 'fairness', 0.95, 'Fairness assessment and bias mitigation', ARRAY[], true),
('aif360', 'python', 'fairness', 0.95, 'IBM AI Fairness 360', ARRAY[], true),
('themis-ml', 'python', 'fairness', 0.90, 'Fairness-aware ML', ARRAY[], true),

-- Data Processing (supporting signals, not AI)
('pandas', 'python', 'data_processing', 0.30, 'Data manipulation — weak signal alone', ARRAY[], false),
('numpy', 'python', 'data_processing', 0.20, 'Numerical computing — very weak signal', ARRAY[], false),
('polars', 'python', 'data_processing', 0.20, 'Fast dataframes', ARRAY[], false),

-- MLOps
('mlflow', 'python', 'mlops', 0.50, 'Experiment tracking and model registry', ARRAY[], true),
('wandb', 'python', 'mlops', 0.50, 'Weights & Biases experiment tracking', ARRAY[], true),
('bentoml', 'python', 'mlops', 0.40, 'Model serving framework', ARRAY[], true);

-- ============================================================================
-- Framework Signatures (JavaScript)
-- ============================================================================
INSERT INTO framework_signatures (name, ecosystem, category, hr_relevance_score, description, aliases, is_ai_framework) VALUES
('@tensorflow/tfjs', 'javascript', 'ml_deep_learning', 0.40, 'TensorFlow.js', ARRAY['tensorflow'], true),
('openai', 'javascript', 'llm', 0.60, 'OpenAI Node.js client', ARRAY[], true),
('@anthropic-ai/sdk', 'javascript', 'llm', 0.60, 'Anthropic Claude SDK', ARRAY[], true),
('langchain', 'javascript', 'llm_orchestration', 0.60, 'LangChain JS/TS', ARRAY['@langchain/core'], true),
('llamaindex', 'javascript', 'llm_orchestration', 0.50, 'LlamaIndex JS/TS', ARRAY[], true),
('brain.js', 'javascript', 'ml_deep_learning', 0.30, 'Neural networks for JS', ARRAY[], true),
('ml5', 'javascript', 'ml_general', 0.20, 'Friendly ML for the web', ARRAY[], true);

-- ============================================================================
-- Regulatory Map — EU AI Act, Annex III Category 4 (Employment)
-- ============================================================================

-- Article 9: Risk Management System
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_9', 'Risk Management System', '4', '4a',
 '[
   {"check_id": "art9_risk_doc", "name": "Risk assessment documentation", "type": "file_presence", "patterns": ["risk_assessment*", "risk_management*", "RISK*"], "required": true},
   {"check_id": "art9_risk_process", "name": "Risk management process defined", "type": "content_analysis", "look_for": ["risk identification", "risk mitigation", "residual risk"], "required": true},
   {"check_id": "art9_testing", "name": "Testing against risk measures", "type": "file_presence", "patterns": ["tests/risk*", "tests/safety*", "test_risk*"], "required": true}
 ]',
 'CRITICAL', 'Providers must establish a risk management system throughout the AI lifecycle', '2026-08-02'),

('EU_AI_ACT', 'ART_9', 'Risk Management System', '4', '4b',
 '[
   {"check_id": "art9_risk_doc", "name": "Risk assessment documentation", "type": "file_presence", "patterns": ["risk_assessment*", "risk_management*", "RISK*"], "required": true},
   {"check_id": "art9_monitoring", "name": "Ongoing risk monitoring", "type": "content_analysis", "look_for": ["monitoring", "drift detection", "performance degradation"], "required": true}
 ]',
 'CRITICAL', 'Risk management for promotion/termination/monitoring AI', '2026-08-02'),

('EU_AI_ACT', 'ART_9', 'Risk Management System', '4', '4c',
 '[
   {"check_id": "art9_risk_doc", "name": "Risk assessment documentation", "type": "file_presence", "patterns": ["risk_assessment*", "risk_management*", "RISK*"], "required": true},
   {"check_id": "art9_worker_rights", "name": "Worker rights impact assessment", "type": "content_analysis", "look_for": ["worker rights", "privacy impact", "proportionality"], "required": true}
 ]',
 'CRITICAL', 'Risk management for worker monitoring AI', '2026-08-02');

-- Article 10: Data and Data Governance
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_10', 'Data and Data Governance', '4', '4a',
 '[
   {"check_id": "art10_dataset_doc", "name": "Training data documentation", "type": "file_presence", "patterns": ["data_card*", "dataset_card*", "DATA_README*", "datasheet*"], "required": true},
   {"check_id": "art10_bias_analysis", "name": "Bias and representativeness analysis", "type": "file_presence", "patterns": ["bias_report*", "fairness_report*", "demographic_analysis*"], "required": true},
   {"check_id": "art10_data_provenance", "name": "Data provenance tracking", "type": "content_analysis", "look_for": ["data source", "collection method", "data provenance", "data lineage"], "required": true},
   {"check_id": "art10_bias_code", "name": "Bias detection in code", "type": "code_analysis", "look_for": ["fairlearn", "aif360", "bias", "demographic_parity", "equalized_odds"], "required": false}
 ]',
 'CRITICAL', 'Training data must be relevant, representative, and free of errors', '2026-08-02'),

('EU_AI_ACT', 'ART_10', 'Data and Data Governance', '4', '4b',
 '[
   {"check_id": "art10_dataset_doc", "name": "Training data documentation", "type": "file_presence", "patterns": ["data_card*", "dataset_card*", "DATA_README*"], "required": true},
   {"check_id": "art10_performance_data", "name": "Performance evaluation data documented", "type": "content_analysis", "look_for": ["evaluation dataset", "test set", "validation data"], "required": true}
 ]',
 'CRITICAL', 'Data governance for promotion/termination AI', '2026-08-02');

-- Article 11: Technical Documentation
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_11', 'Technical Documentation', '4', '4a',
 '[
   {"check_id": "art11_model_card", "name": "Model card or technical spec", "type": "file_presence", "patterns": ["MODEL_CARD*", "model_card*", "technical_spec*", "ARCHITECTURE*"], "required": true},
   {"check_id": "art11_intended_purpose", "name": "Intended purpose documented", "type": "content_analysis", "look_for": ["intended purpose", "intended use", "use case", "designed for"], "required": true},
   {"check_id": "art11_limitations", "name": "Known limitations documented", "type": "content_analysis", "look_for": ["limitation", "constraint", "known issue", "out of scope"], "required": true},
   {"check_id": "art11_architecture", "name": "System architecture documented", "type": "file_presence", "patterns": ["ARCHITECTURE*", "architecture*", "system_design*", "docs/design*"], "required": true}
 ]',
 'HIGH', 'Technical documentation must be drawn up before placing on market', '2026-08-02');

-- Article 13: Transparency and Information to Deployers
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_13', 'Transparency and Information to Deployers', '4', '4a',
 '[
   {"check_id": "art13_user_disclosure", "name": "AI involvement disclosed to users", "type": "content_analysis", "look_for": ["AI-assisted", "automated decision", "algorithm", "machine learning", "AI system"], "required": true},
   {"check_id": "art13_instructions", "name": "Instructions for use provided", "type": "file_presence", "patterns": ["USAGE*", "instructions*", "user_guide*", "deployer_guide*"], "required": true},
   {"check_id": "art13_capabilities", "name": "Capabilities and limitations communicated", "type": "content_analysis", "look_for": ["accuracy", "performance", "limitation", "error rate"], "required": true}
 ]',
 'HIGH', 'High-risk AI systems must be transparent to deployers', '2026-08-02');

-- Article 14: Human Oversight
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_14', 'Human Oversight', '4', '4a',
 '[
   {"check_id": "art14_hitl", "name": "Human-in-the-loop mechanism", "type": "code_analysis", "look_for": ["human_review", "manual_review", "approval_required", "human_override", "human_in_the_loop"], "required": true},
   {"check_id": "art14_override", "name": "Override or stop capability", "type": "code_analysis", "look_for": ["override", "disable", "stop", "kill_switch", "circuit_breaker"], "required": true},
   {"check_id": "art14_interpretability", "name": "Output interpretability", "type": "code_analysis", "look_for": ["explain", "interpretab", "shap", "lime", "feature_importance"], "required": false}
 ]',
 'CRITICAL', 'High-risk AI must allow effective human oversight', '2026-08-02');

-- Article 15: Accuracy, Robustness, Cybersecurity
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('EU_AI_ACT', 'ART_15', 'Accuracy, Robustness and Cybersecurity', '4', '4a',
 '[
   {"check_id": "art15_accuracy_metrics", "name": "Accuracy metrics documented", "type": "file_presence", "patterns": ["eval_results*", "metrics*", "benchmark*", "performance_report*"], "required": true},
   {"check_id": "art15_test_suite", "name": "Test suite exists", "type": "file_presence", "patterns": ["tests/*", "test_*", "*_test.py"], "required": true},
   {"check_id": "art15_robustness", "name": "Robustness testing", "type": "content_analysis", "look_for": ["adversarial", "robustness", "edge case", "stress test", "out of distribution"], "required": false},
   {"check_id": "art15_security", "name": "Security measures documented", "type": "file_presence", "patterns": ["SECURITY*", "security*", "threat_model*"], "required": false}
 ]',
 'HIGH', 'High-risk AI must achieve appropriate accuracy and robustness', '2026-08-02');

-- ============================================================================
-- Regulatory Map — Colorado SB24-205 (supplementary)
-- ============================================================================
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('CO_SB24_205', 'SEC_6', 'Algorithmic Discrimination Prevention', '4', '4a',
 '[
   {"check_id": "co_impact_assessment", "name": "Algorithmic impact assessment", "type": "file_presence", "patterns": ["impact_assessment*", "algorithmic_audit*"], "required": true},
   {"check_id": "co_bias_testing", "name": "Discrimination testing by protected class", "type": "content_analysis", "look_for": ["protected class", "race", "gender", "age", "disability", "disparate impact"], "required": true}
 ]',
 'HIGH', 'Developers must use reasonable care to protect against algorithmic discrimination', '2026-02-01');

-- ============================================================================
-- Regulatory Map — NYC Local Law 144 (supplementary)
-- ============================================================================
INSERT INTO regulatory_map (jurisdiction, article, title, category, subcategory, technical_checks, severity, description, effective_date) VALUES
('NYC_LL144', 'SEC_5', 'Automated Employment Decision Tools', '4', '4a',
 '[
   {"check_id": "nyc_bias_audit", "name": "Annual bias audit by independent auditor", "type": "file_presence", "patterns": ["bias_audit*", "annual_audit*", "ll144_audit*"], "required": true},
   {"check_id": "nyc_notice", "name": "Notice to candidates", "type": "content_analysis", "look_for": ["notice to candidates", "automated employment", "AEDT notice"], "required": true},
   {"check_id": "nyc_impact_ratio", "name": "Impact ratio calculation", "type": "content_analysis", "look_for": ["impact ratio", "selection rate", "four-fifths rule", "adverse impact"], "required": true}
 ]',
 'HIGH', 'AEDTs require annual bias audits and candidate notification', '2023-07-05');
