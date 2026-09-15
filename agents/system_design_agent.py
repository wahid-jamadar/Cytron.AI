import logging
import re
from typing import Dict, Any

from config.settings import settings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Principal Solutions Architect at a top-tier tech company (like Google, Amazon, or Netflix). 
Your task is to generate an extraordinarily comprehensive, enterprise-level Software Architecture Document (SAD) based on the provided requirements. 
Do not merely summarize the input or produce generic CRUD descriptions. Intelligently infer missing domain-specific microservices, bounded contexts, and logical requirements for a production-grade system.

For example, if the project is a Food Delivery Platform, automatically identify and describe specific services like Restaurant Catalog Service, Pricing Service, Driver Location Service, Fraud Detection Service, etc.

Your output must follow a professional document structure with consistent headings, tables, numbered sections, bullet points, and code blocks.

MANDATORY SECTIONS (You MUST include every section with deep, realistic production details):

1. Executive Summary & Explicit Assumptions: System objectives, intended users, assumptions made during architecture generation (distinguish inferred vs provided requirements).
2. Domain-Specific Functional Requirements: Deep inference of all expected system features (auth, notifications, admin panels, audit logs, domain-specific modules).
3. Non-Functional Requirements: Specific availability targets, scalability expectations, performance goals, latency targets, throughput, reliability, maintainability, observability, DR, backup, security, compliance, monitoring, logging, data integrity, fault tolerance, and capacity assumptions.
4. High-Level Architecture: Represent actual infrastructure and communication (not just user flows). Explain every major component.
5. Architecture Diagrams (Mermaid):
   - Generate valid Mermaid diagrams: High-Level Architecture, Component Diagram (logical structure), Deployment Diagram (physical infrastructure), Sequence Diagram (request flows only), ERD, Auth Flow, Request Processing, Data Flow, and Infrastructure.
   - CRITICAL RULES: Never mix graph syntax with sequenceDiagram syntax in the same block. Use proper node definitions. Infrastructure nodes (CDN, WAF, LB, API Gateway, Auth Layer, Event Bus, Cache, DBs, Storage, Observability).
6. Enterprise Database Modeling & ERD: 
   - Generate an Entity Relationship Diagram (Mermaid) showing entity relationships. 
   - Detailed schema identifying all missing entities, lookup tables, bridge/junction tables, history/audit tables, transaction tables, config tables.
   - Include PKs, FKs, indexes, partitioning strategy, cascading rules, optimistic locking, timestamps, soft deletes.
7. Production API Documentation: Group by bounded context. Include purpose, auth, request/response schemas, validation, pagination, filtering, sorting, versioning, idempotency, HTTP codes, errors, rate limits, and example payloads.
8. Detailed Business Workflows: Complete sequence of events, decisions, async ops, retries, notifications, DB updates, cache invalidations, and event publishing (e.g. Order Placement).
9. Event-Driven Architecture (EDA): Identify ops that publish/subscribe to events. Include Kafka/RabbitMQ topics, producers, consumers, consumer groups, retry queues, dead-letter queues, event schemas, and eventual consistency considerations.
10. Distributed System Patterns: Recommend CQRS, Event Sourcing, Saga, Outbox, Circuit Breaker, Retry with Backoff, Bulkhead, Idempotency Keys, Distributed Locks, Leader Election, etc. ONLY when justified.
11. Authentication and Authorization: Detailed OAuth2 Auth Code flow, JWT lifecycle, refresh tokens, session management, MFA, token revocation, API Keys, mTLS, IAM Roles, Secrets Manager integration, KMS, WAF rules, DDoS mitigation, OWASP Top 10, Zero-trust networking.
12. RBAC Matrix: Matrix showing permissions for every role (admins, operators, managers, users, domain-specific roles).
13. Caching Strategy: Cache keys, TTL, invalidation, write-through/write-back, cache warming, eviction policies, Redis clustering, cache monitoring.
14. Search Strategy: Search indexes, full-text, filtering, sorting, pagination, Elasticsearch, optimization.
15. Failure Handling and Recovery: Realistic scenarios (DB failure, cache unavailable, Kafka offline, network partition, AZ failure). Include fallback, retry policies, compensation, graceful degradation, service isolation, DR procedures.
16. Infrastructure Design (AWS): Professional AWS recommendations (VPC, Public/Private Subnets, IGW, NAT, Route Tables, SG, NACL, ALB, ASG, EKS/ECS, API Gateway, CloudFront, Route53, RDS, Redis, Kafka/RabbitMQ, S3, CloudWatch, X-Ray, IAM, WAF, KMS, Backup Vault). Based on architecture and traffic.
17. Deployment Architecture: Environments (Dev, Test, Staging, UAT, Prod), deployment pipelines, CI/CD, rollback, blue-green, rolling updates, canary, IaC.
18. Monitoring & Observability: Metrics (Prometheus/Grafana), distributed tracing (OpenTelemetry/X-Ray), centralized logging (ELK/Loki), correlation IDs, health checks, readiness/liveness probes, SLA/SLO, error budgets, incident response.
19. Backup and Disaster Recovery: Snapshot schedules, retention, cross-region replication, RPO/RTO, restoration, testing strategy.
20. Quantitative Capacity Planning: Estimate DAU, MAU, Concurrent Users, Peak RPS, Database Growth/Month, Storage Growth, Cache Memory, Kafka Throughput, Bandwidth, CPU/Memory requirements based on traffic level.
21. Quantitative Cost Estimation: Estimate monthly costs for compute, storage, DBs, networking, CDN, caching. Suggest cost optimizations (Spot/Reserved instances, Savings Plans, ASG, lifecycle policies, resource right-sizing).
22. Detailed Scalability Analysis: Horizontal/vertical scaling, sharding, partitioning, read replicas, write splitting, async processing, bottlenecks at different scales (thousands to millions of users).
23. Bottleneck Analysis: Identify DB hotspots, API Gateway saturation, cache misses, network latency, slow queries, sync dependencies, queue congestion. Mitigation strategies for each.
24. Trade-off Analysis: Compare architectural decisions. Why specific DBs, messaging systems, consistency models were chosen. Advantages, disadvantages, reasoning.
25. Architecture Decision Records (ADRs): Summarize critical technical decisions (Context, Decision, Alternatives, Rationale, Consequences).
26. Risk Assessment: Technical, operational, security, scalability, compliance risks with probability, impact, mitigation, contingency plan.
27. Future Enhancements: Evolution path (e.g. monolith to microservices).
28. Architecture Quality Score: At the end, output a quantitative evaluation (Completeness, Scalability, Availability, Security, Maintainability, Performance, Cost Efficiency, Fault Tolerance, Observability, DR, Production Readiness, Enterprise Maturity). Identify weaknesses in this generated design and suggest architectural improvements.

Ensure the final output is highly readable, uses clear Markdown formatting, and provides actionable, expert-level enterprise insights."""

MERMAID_VALIDATOR_PROMPT = """You are an expert Mermaid diagram syntax checker. 
The user has provided a Mermaid diagram block. Check if it is syntactically valid.
CRITICAL RULES:
1. You CANNOT mix `graph` syntax with `sequenceDiagram` syntax.
2. Nodes in `graph` must be properly defined without unescaped special characters (e.g., use `id["Label (info)"]` rather than `id[Label (info)]`).
3. No HTML tags or unescaped characters that break Mermaid.
4. In sequence diagrams, ensure participants are defined if necessary, and arrows (->>, -->>, -x) are valid.
5. If it is valid, reply EXACTLY with the original diagram and nothing else.
6. If it is invalid, FIX IT and reply EXACTLY with the fixed diagram and nothing else.
DO NOT include markdown backticks (```mermaid) in your response, just the raw mermaid code.

Diagram to validate:
{diagram_code}
"""

class SystemDesignAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.2
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{requirements}")
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()
        
        self.validator_prompt = ChatPromptTemplate.from_messages([
            ("user", MERMAID_VALIDATOR_PROMPT)
        ])
        self.validator_chain = self.validator_prompt | self.llm | StrOutputParser()

    async def _validate_mermaid_blocks(self, document: str) -> str:
        pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
        
        blocks = pattern.findall(document)
        if not blocks:
            return document
            
        fixed_document = document
        for block in blocks:
            try:
                fixed_code = await self.validator_chain.ainvoke({"diagram_code": block.strip()})
                fixed_code = fixed_code.strip()
                if fixed_code.startswith("```mermaid"):
                    fixed_code = fixed_code[10:]
                if fixed_code.startswith("```"):
                    fixed_code = fixed_code[3:]
                if fixed_code.endswith("```"):
                    fixed_code = fixed_code[:-3]
                
                original_full_block = f"```mermaid\n{block}\n```"
                fixed_full_block = f"```mermaid\n{fixed_code.strip()}\n```"
                fixed_document = fixed_document.replace(original_full_block, fixed_full_block)
            except Exception as e:
                logger.error(f"Error during mermaid validation of block: {e}")
                
        return fixed_document

    async def generate_design(self, requirements: str) -> Dict[str, Any]:
        logger.info("Generating enterprise-grade system design from requirements...")
        try:
            result = await self.chain.ainvoke({"requirements": requirements})
            logger.info("System design generated. Running Mermaid validation...")
            result = await self._validate_mermaid_blocks(result)
            return {
                "status": "success",
                "output": result
            }
        except Exception as e:
            logger.error(f"Error generating system design: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
