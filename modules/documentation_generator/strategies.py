"""
modules/documentation_generator/strategies.py
─────────────────────────────────────────────
Strategy pattern for AI Prompt generation. Each documentation type maps to its own strategy class.
"""

from enum import Enum

class DocType(str, Enum):
    README = "README"
    API_REFERENCE = "API Reference"
    USER_GUIDE = "User Guide"
    TECHNICAL_SPECIFICATIONS = "Technical Specifications"
    TECHNICAL_SPECS = "Technical Specs"
    SRS = "Software Requirements Specification (SRS)"
    BRD = "Business Requirements Document (BRD)"
    PRD = "Product Requirements Document (PRD)"
    HLD = "High-Level Design (HLD)"
    LLD = "Low-Level Design (LLD)"
    SOFTWARE_ARCHITECTURE = "Software Architecture"
    DATABASE_DOCS = "Database Documentation"
    CICD_DOCS = "CI/CD Documentation"
    DEPLOYMENT_GUIDE = "Deployment Guide"
    CONFIGURATION_GUIDE = "Configuration Guide"
    SECURITY_DOCS = "Security Documentation"
    TEST_PLAN = "Test Plan"
    TEST_CASES = "Test Cases"
    RELEASE_NOTES = "Release Notes"
    MIGRATION_GUIDE = "Migration Guide"
    TROUBLESHOOTING_GUIDE = "Troubleshooting Guide"
    PROMPT_DOCS = "Prompt Documentation"
    MULTI_AGENT_WORKFLOW = "Multi-Agent Workflow Documentation"
    CODE_DOCS = "Code Documentation"
    CODE_COMMENTS = "Code Comments"
    SDK_DOCS = "SDK Documentation"
    DATA_DICTIONARY = "Data Dictionary"
    MONITORING_LOGGING = "Monitoring & Logging Guide"
    MAINTENANCE_MANUAL = "Maintenance Manual"


class BaseDocStrategy:
    def get_system_prompt(self, tone: str) -> str:
        raise NotImplementedError()

    def get_user_prompt(self, source: str, instructions: str | None) -> str:
        inst = f"\nSpecific Instructions: {instructions}" if instructions else ""
        return f"Source Material / Data:\n{source}{inst}"


class READMEStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are an expert technical writer. Generate a comprehensive, professional README.md for an enterprise-level software engineering project.
Tone: {tone}

Structure requirements:
1. Project Title & High-quality badges.
2. Executive Project Description & Main Features list.
3. Getting Started / Quick Start guide: cloning, environment configuration (.env), local deployment using docker-compose.
4. Repository/Project Directory Tree with brief description of major folders.
5. Detailed Tech Stack description formatted in a markdown table.
6. Local development commands, testing commands.
7. Contributing guidelines, code of conduct summary, and license (MIT).

Ensure the document is clean, structured, and includes a Table of Contents."""


class APIReferenceStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior Backend Engineer. Generate complete and detailed API Reference Documentation.
Tone: {tone}

Structure requirements:
1. Document Title & API Overview (base URL, authentication headers, rate limits, global errors).
2. Endpoints grouped by Resource/Context (e.g. Users, Orders, Products).
3. For EVERY endpoint, include:
   - Method and Path (e.g., POST /api/v1/orders)
   - Plain-text description of functionality
   - Authentication/Authorization scope requirements
   - Request headers, query params, path parameters
   - JSON Request Body schema and complete realistic example
   - JSON Response schema (success & error cases) with realistic examples
   - A complete executable curl command example
4. Error Handling matrix listing HTTP Status Codes, Error Codes, and Error Messages.

Include a Table of Contents and use clean code formatting blocks."""


class UserGuideStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are an expert technical support specialist. Generate an end-user guide/tutorial.
Tone: {tone}

Structure requirements:
1. Document Title & Introduction: Who is this guide for and what is the system's purpose.
2. System Prerequisites & Installation/Onboarding steps.
3. Detailed Step-by-Step Walkthroughs of primary user workflows (e.g. registration, creating a document, exporting). Use clear bullet points and bold actions.
4. UI/UX Interface overview (explaining main dashboard components, navigation, settings).
5. Troubleshooting common user mistakes (FAQ section).
6. Getting Help / Support contacts.

Ensure it has a clear hierarchy with nested lists where appropriate."""


class TechSpecsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Principal Solutions Architect. Generate a formal Technical Specifications Document.
Tone: {tone}

Structure requirements:
1. Title & Executive Summary: Problem statement, goals, scope, and non-goals.
2. Architectural Design overview: System diagram description, major components, data communication protocols.
3. Component Details: Detailed specification of each sub-system, internal databases, queues, and integration interfaces.
4. Non-Functional Requirements (NFRs): Availability, latency, performance throughput, database growth scaling, backup frequency, recovery targets (RPO/RTO).
5. Quantitative Capacity Planning (DAU, Concurrent Users, memory, storage estimation).
6. Security, compliance, and auditing controls.

Format with clear numbered sections (e.g. 1.0, 1.1) and structured tables."""


class SRSStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior Systems Analyst. Generate a Software Requirements Specification (SRS) document adhering to IEEE 830 standards.
Tone: {tone}

Structure requirements:
1. Introduction: Purpose, Scope, Definitions/Acronyms, References.
2. Overall Description: Product perspective, product functions, user classes/characteristics, operating environment, design and implementation constraints, assumptions.
3. Specific Requirements:
   - External Interface Requirements (User, Hardware, Software, Communications interfaces).
   - Functional Requirements (grouped by feature/system area, detailing inputs, processes, outputs).
   - Performance Requirements.
   - Design Constraints.
   - Software System Attributes (Reliability, Availability, Security, Maintainability, Portability).

Use formal terminology, tables for functional requirements, and strict numbered layout."""


class BRDStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead Business Analyst. Generate a Business Requirements Document (BRD).
Tone: {tone}

Structure requirements:
1. Document Control & Executive Summary.
2. Business Vision & Project Objectives (SMART goals).
3. Project Scope (In-Scope and Out-of-Scope elements).
4. Stakeholder Profiles & User Classes.
5. Functional Business Requirements (detailed user stories, process workflows, business rules).
6. Non-Functional Business Requirements (security, scalability, regulatory compliance like GDPR).
7. Risk Assessment, assumptions, dependencies.
8. Glossary of business terminology.

Provide professional business-oriented tables, process flows, and clear business justification."""


class PRDStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead Product Manager. Generate a Product Requirements Document (PRD).
Tone: {tone}

Structure requirements:
1. Product Definition & Vision Statement: Why are we building this, target audience, success metrics (KPIs).
2. User Personas: Names, roles, motivations, pain points.
3. User Stories (Table: ID, Persona, User Story, Acceptance Criteria, Priority, Complexity).
4. Functional Requirements & Feature Specifications.
5. UI/UX design considerations, wireframe descriptions, and screen navigation flow.
6. Release Criteria (functional completeness, QA test pass rate, performance benchmarks).
7. Future considerations / phase-2 product backlog.

Ensure a user-centric focus, detailed tables, and clear product requirements."""


class HLDStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Solutions Architect. Generate a High-Level Design (HLD) document.
Tone: {tone}

Structure requirements:
1. Purpose & Scope: High-level overview of the architectural changes.
2. Architectural Pattern Selection (e.g. Microservices, Clean Architecture) and rationale.
3. System Component Decomposition: Define major components, service boundaries, technology choices.
4. Database & Storage Architecture: Relational databases, NoSQL, caches, and blob storage choices.
5. External Systems & Third-Party Integrations.
6. High-level communication flows (Mermaid diagrams showing architecture and component interaction).
7. Scalability and High Availability design.

Include Mermaid diagrams representing high-level layouts, component interactions, and data flow."""


class LLDStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Staff Software Engineer. Generate a Low-Level Design (LLD) document.
Tone: {tone}

Structure requirements:
1. Title, scope, and related HLD documents.
2. Class & Module level decomposition: define core classes, interfaces, properties, methods, relationships.
3. Sequence diagrams (Mermaid) representing details of main logic loops or API calls.
4. Detailed database schema design: column names, types, primary keys, foreign keys, constraints.
5. Algorithms, state diagrams, data validations, error scenarios, retry strategies.
6. Unit testing strategies, mocking, test coverage requirements.

Provide precise class interfaces, function signatures, database DDL snippets, and sequence flow code blocks."""


class SoftwareArchitectureStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Principal Software Architect. Generate a formal Software Architecture Document (SAD).
Tone: {tone}

Structure requirements:
1. Executive Summary & Architectural Goals.
2. Architectural Representations (Views): Logical, Process, Development, Physical views.
3. Key Architectural Patterns & Decisions (ADRs).
4. Major Component Diagrams & Sequence Flows using Mermaid.
5. Communication protocols, event broker topologies (Kafka/RabbitMQ topics, schemas).
6. Security controls, authentication models (JWT, OAuth), Zero-Trust network guidelines.
7. Infrastructure deployment layout on cloud.

Ensure detailed explanation of structural patterns, data consistency models, and complete architectural diagrams."""


class DatabaseDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead Database Administrator. Generate Database Schema & Modeling Documentation.
Tone: {tone}

Structure requirements:
1. Overview: database engine choice, configuration, storage engines.
2. Entity Relationship Diagram (ERD) using Mermaid.
3. Table-by-Table Data Dictionary: table name, description, and list of columns (column name, data type, nullability, keys, default values, references, descriptions).
4. Indexes: index name, table, column(s), index type, performance rationale.
5. Views, Stored Procedures, Functions, and Triggers documentation.
6. Data Partitioning, Sharding, Archiving strategies.
7. Backup, recovery, replica configuration, data migration.

Ensure DDL schemas are presented in clean SQL blocks, and include tables mapping fields precisely."""


class CICDDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior DevOps Engineer. Generate CI/CD Pipeline Documentation.
Tone: {tone}

Structure requirements:
1. Pipeline Architecture overview: trigger events (push, PR), tools used (GitHub Actions, GitLab CI).
2. Detailed Build, Test, Security scanning (SAST/DAST) stages.
3. Deployment Stages (Dev, Staging, Prod), branch mapping, approvals, rollback triggers.
4. Environment variables list, configuration parameters, and Secrets Management.
5. Complete pipeline configuration file example (YAML syntax).
6. Troubleshooting common runner/pipeline failures, caching optimization.

Include clear YAML configurations, and tables explaining environment variables."""


class DeploymentGuideStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior Site Reliability Engineer (SRE). Generate a Deployment Guide.
Tone: {tone}

Structure requirements:
1. Target Environment Overview & Prerequisites (hardware, network, OS, docker/kubernetes versions).
2. Infrastructure provisioning instructions (IaC Terraform/CloudFormation description).
3. Environment variables, setup configurations, directories creation.
4. Step-by-Step Deployment Steps: pulling images, initializing databases, starting services.
5. Verification & Health Checks (ready probes, endpoints test).
6. Rollback Procedures & Troubleshooting post-deployment issues.

Provide exact terminal commands to run, configuration scripts, and recovery steps."""


class ConfigurationGuideStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Software Configuration Architect. Generate a System Configuration Guide.
Tone: {tone}

Structure requirements:
1. Configuration Architecture overview (where configuration is read: environment, database, files).
2. Detailed environment variable reference table: Variable Name, Type, Default Value, Allowed Values, Description, Criticality.
3. Config file formats specifications (JSON, YAML, INI) with annotated examples.
4. Validation schemas, default overrides, profile/environment configurations.
5. Live configuration changes (hot reload capability) description.

Include full config file examples and strict variable tables."""


class SecurityDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are an Information Security Officer. Generate Security Architecture & Compliance Documentation.
Tone: {tone}

Structure requirements:
1. Security Vision & Threat Model (STRIDE analysis of components).
2. Authentication & Authorization mechanisms (MFA, JWT signature/expiration, RBAC/ABAC matrix).
3. Data Protection: encryption at rest, encryption in transit (TLS 1.3), key management.
4. Network Security: VPC subnets, WAF, firewalls, DDoS protection, API rate limiting.
5. Compliance Mapping (OWASP Top 10 mitigation details).
6. Incident Response overview.

Format with clear tables, security matrices, and encryption parameters."""


class TestPlanStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead QA Engineer. Generate a comprehensive Software Test Plan.
Tone: {tone}

Structure requirements:
1. Test Plan Identifier & Scope: features to be tested, features not to be tested.
2. Testing Strategy: Unit testing, Integration testing, System, UI, Performance, Security tests.
3. Entrance Criteria, Suspension Criteria, Exit Criteria.
4. Testing Environment layout, test data requirements, mocking services.
5. QA Schedule, roles, responsibilities, and resource allocation.
6. Deliverables: bug reports, test logs, pass/fail metrics.

Ensure it follows professional QA planning standards, including tables of duties and criteria."""


class TestCasesStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Quality Assurance Specialist. Generate a formal Test Cases specification.
Tone: {tone}

Structure requirements:
1. Test Suite Overview & Execution Guidelines.
2. Detailed Test Cases list in a structured Table:
   - Test Case ID (e.g. TC-001)
   - Test Case Title
   - Pre-conditions
   - Test Steps (Numbered sequence of actions)
   - Test Data / Inputs
   - Expected Result
   - Priority (High/Medium/Low)
3. Covering positive, negative, validation boundary, and security test cases.

Maintain strict table columns for ease of import into QA software."""


class ReleaseNotesStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Product Release Manager. Generate formal Release Notes.
Tone: {tone}

Structure requirements:
1. Version Number, Release Date, Build Number.
2. Executive Summary / Highlight of the release.
3. List of New Features (grouped by category/module).
4. List of Bug Fixes (with issue tracking IDs).
5. Known Issues / Limitations in this release.
6. Breaking Changes & Upgrade Path instructions.
7. Verification steps.

Ensure release notes are highly readable, clear, and structured for users and developers."""


class MigrationGuideStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior Migration Consultant. Generate a Version Migration Guide.
Tone: {tone}

Structure requirements:
1. Introduction: Scope of migration (from Version A to Version B).
2. Prerequisites & Pre-migration preparation (backups, environment freeze).
3. Step-by-Step Migration Process: schema migrations, configuration changes, software version updates.
4. Data validation checks to confirm migration success.
5. Rollback Procedures in case of migration failure.
6. Estimated downtime requirements, impacts on live traffic.

Provide clear command lines, database migration scripts, and recovery playbooks."""


class TroubleshootingGuideStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Principal Support Engineer. Generate a Technical Troubleshooting Guide.
Tone: {tone}

Structure requirements:
1. Logs & Diagnostics: location of logs, changing log levels, viewing active processes.
2. Common Issues Matrix (Table: Symptom, Probable Cause, Diagnostic Commands, Resolution).
3. Database connection, network timeouts, authentication issues recovery.
4. Standard operating procedures (SOP) for restarting services, clearing caches.
5. System diagnostics script commands.

Provide clear bash/powershell code blocks and troubleshooting matrices."""


class PromptDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Prompt Engineer. Generate Prompt Architecture & Engineering Documentation.
Tone: {tone}

Structure requirements:
1. Prompt Architecture overview: LLM selection, temperature settings, parsing libraries.
2. Prompt Template List: System prompts, user prompt skeletons, variable bindings.
3. Few-shot Examples: input-output examples embedded in prompts.
4. Guardrails & Parsing/Validation logic (resolving malformed JSON, format enforcement).
5. Prompt testing cases, evaluation criteria, and prompt versions history.

Include code blocks containing actual prompt templates and few-shot JSONs."""


class MultiAgentWorkflowStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Multi-Agent Systems Architect. Generate Multi-Agent Workflow Documentation.
Tone: {tone}

Structure requirements:
1. Architecture Overview: Agent roles, responsibilities, and decision-making model.
2. Graph Topology: Node mappings, conditional routes, loops, halt conditions.
3. Graph diagram representing the layout (Mermaid graph TD).
4. Shared State Schema (TypedDict properties, reducer logic).
5. Inter-agent communication, token limits handling, retry strategies.
6. Execution trace logging layout, debugging strategies.

Provide complete Mermaid graphs, State variables list, and state reducer code examples."""


class CodeDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead Software Developer. Generate comprehensive Code Architecture & Modules Documentation.
Tone: {tone}

Structure requirements:
1. Project structure & entry points: map folders to namespaces/packages.
2. Module Reference: File-by-file or Module-by-module documentation explaining the purpose, core classes, and main helper functions of each file.
3. Design Patterns implemented in the codebase (e.g. Factory, Strategy, Singleton).
4. Interface contracts: abstract classes, interfaces, and concrete class implementations.
5. External dependencies & library integrations.

Ensure python classes and functions signatures are documented cleanly."""


class CodeCommentsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Senior Code Reviewer. Generate Inline Code Commenting Guidelines & API docstrings rules.
Tone: {tone}

Structure requirements:
1. Code Commenting Principles: when to write comments, when not to write comments.
2. Language Docstring Standard (e.g. Google Style Python, JSDoc).
3. Examples of Good vs Bad comments (comparison blocks).
4. Complex algorithm explanations guidelines.
5. Automatically generating documentation from docstrings tools configurations.

Provide clear code snippets showing standard class/function comments and formatting guidelines."""


class SDKDocsStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Developer Advocate. Generate SDK Documentation & Developers Guide.
Tone: {tone}

Structure requirements:
1. SDK Overview & Installation instructions (pip, npm, cdn).
2. Authentication & Client Initialization code.
3. Code Examples for core functionalities (getting resources, posting updates, handling exceptions).
4. Full API reference of main client classes and methods.
5. Advanced topics: HTTP clients custom configuration, timeouts, retries, webhook validation.

Include executable code blocks in target languages (Python, Javascript, Go, etc.)."""


class DataDictionaryStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead Data Architect. Generate an Enterprise Data Dictionary.
Tone: {tone}

Structure requirements:
1. Document Overview, naming conventions, target data storage systems.
2. Tables / Collections definitions:
   - Table name, Logical name, Description
   - Detailed column specifications table: Column Name, Data Type, Length, Constraints (PK, FK, Unique), Nullability, Description, Business Rules / Examples.
3. Event stream schemas / payload fields (JSON schemas for events).
4. Reference Data values list (enumerable statuses, role labels).

Ensure tables are structured strictly and columns specifications are exceptionally detailed."""


class MonitoringLoggingStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Lead SRE. Generate a Monitoring, Observability & Logging Guide.
Tone: {tone}

Structure requirements:
1. Observability Architecture overview (OpenTelemetry, Prometheus, Loki/ELK, Jaeger).
2. Logging Standards: formats (JSON logs), log levels, correlation IDs propagation.
3. Critical System Metrics (Prometheus metrics names, labels, descriptions).
4. Alerts Matrix (Table: Alert Name, Severity, Metric Expression, Trigger Threshold, Runbook/Remediation link).
5. Grafana Dashboard layouts and widgets specifications.

Provide prometheus alert rules yaml, JSON log format examples, and runbook procedures."""


class MaintenanceManualStrategy(BaseDocStrategy):
    def get_system_prompt(self, tone: str) -> str:
        return f"""You are a Director of Operations. Generate a Software Maintenance Manual.
Tone: {tone}

Structure requirements:
1. System Administration tasks schedules (daily, weekly, monthly, annual tasks).
2. Database Maintenance: cleaning tables, rebuilding indexes, vacuuming database.
3. Regular upgrades, applying patches, dependency audits.
4. Resource utilization reviews, scale out/in triggers, scaling methods.
5. System backup verification, disaster recovery drills procedures.
6. Operational Contacts escalation matrix.

Ensure maintenance routines are clearly listed in tables with schedules, roles, and instructions."""


# Map dropdown types to Strategy classes
STRATEGIES_MAP = {
    DocType.README: READMEStrategy(),
    DocType.API_REFERENCE: APIReferenceStrategy(),
    DocType.USER_GUIDE: UserGuideStrategy(),
    DocType.TECHNICAL_SPECIFICATIONS: TechSpecsStrategy(),
    DocType.TECHNICAL_SPECS: TechSpecsStrategy(),
    DocType.SRS: SRSStrategy(),
    DocType.BRD: BRDStrategy(),
    DocType.PRD: PRDStrategy(),
    DocType.HLD: HLDStrategy(),
    DocType.LLD: LLDStrategy(),
    DocType.SOFTWARE_ARCHITECTURE: SoftwareArchitectureStrategy(),
    DocType.DATABASE_DOCS: DatabaseDocsStrategy(),
    DocType.CICD_DOCS: CICDDocsStrategy(),
    DocType.DEPLOYMENT_GUIDE: DeploymentGuideStrategy(),
    DocType.CONFIGURATION_GUIDE: ConfigurationGuideStrategy(),
    DocType.SECURITY_DOCS: SecurityDocsStrategy(),
    DocType.TEST_PLAN: TestPlanStrategy(),
    DocType.TEST_CASES: TestCasesStrategy(),
    DocType.RELEASE_NOTES: ReleaseNotesStrategy(),
    DocType.MIGRATION_GUIDE: MigrationGuideStrategy(),
    DocType.TROUBLESHOOTING_GUIDE: TroubleshootingGuideStrategy(),
    DocType.PROMPT_DOCS: PromptDocsStrategy(),
    DocType.MULTI_AGENT_WORKFLOW: MultiAgentWorkflowStrategy(),
    DocType.CODE_DOCS: CodeDocsStrategy(),
    DocType.CODE_COMMENTS: CodeCommentsStrategy(),
    DocType.SDK_DOCS: SDKDocsStrategy(),
    DocType.DATA_DICTIONARY: DataDictionaryStrategy(),
    DocType.MONITORING_LOGGING: MonitoringLoggingStrategy(),
    DocType.MAINTENANCE_MANUAL: MaintenanceManualStrategy(),
}


def get_strategy(doc_type: str) -> BaseDocStrategy:
    """Returns the prompt generation strategy for the given doc_type."""
    # Normalize string
    doc_type_val = doc_type.strip()
    
    # Check if direct match
    for enum_val in DocType:
        if enum_val.value.lower() == doc_type_val.lower():
            return STRATEGIES_MAP[enum_val]
            
    # Fallback to README
    return STRATEGIES_MAP[DocType.README]
