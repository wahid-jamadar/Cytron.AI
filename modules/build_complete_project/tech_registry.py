"""
modules/build_complete_project/tech_registry.py
─────────────────────────────────────────────────
Technology and Architecture configuration registry for Cytron.AI.
Decouples framework-specific prompts, dependency schemas, and folder structures
from core agent files.
"""

import re
from typing import Dict, List, Any

# ── Dataclasses for Registry Entries ──────────────────────────────────────────

class FrontendConfig:
    def __init__(self, name: str, prompt_guidelines: str, files_schema: str, key_deps: List[str]):
        self.name = name
        self.prompt_guidelines = prompt_guidelines
        self.files_schema = files_schema
        self.key_deps = key_deps


class BackendConfig:
    def __init__(self, name: str, language: str, prompt_guidelines: str, files_schema: str, key_deps: List[str]):
        self.name = name
        self.language = language
        self.prompt_guidelines = prompt_guidelines
        self.files_schema = files_schema
        self.key_deps = key_deps


class ArchitectureConfig:
    def __init__(self, name: str, prompt_guidelines: str):
        self.name = name
        self.prompt_guidelines = prompt_guidelines


# ── Parse Tech Stack ──────────────────────────────────────────────────────────

def parse_tech_stack(user_input: str) -> Dict[str, str]:
    """
    Extract frontend, backend, and architecture from combined prompt string.
    Falls back to default values if not explicitly matched.
    """
    frontend = "React"
    backend = "FastAPI"
    arch = "Monolithic"

    # Match Frontend: <val>
    m_fe = re.search(r"Frontend:\s*([^\n]+)", user_input, re.IGNORECASE)
    if m_fe:
        frontend = m_fe.group(1).strip()

    # Match Backend: <val>
    m_be = re.search(r"Backend:\s*([^\n]+)", user_input, re.IGNORECASE)
    if m_be:
        backend = m_be.group(1).strip()

    # Match Build a complete <val> web application
    m_ar = re.search(r"Build a complete\s+([^\n]+?)\s+web application", user_input, re.IGNORECASE)
    if m_ar:
        arch = m_ar.group(1).strip()

    return {
        "frontend": frontend,
        "backend": backend,
        "architecture": arch
    }


# ── Explicit Configurations Registry ──────────────────────────────────────────

# Fallback presets to ensure any dynamic/unlisted framework has functional defaults
DEFAULT_FRONTEND = FrontendConfig(
    name="Vite React",
    prompt_guidelines="- Use Vite dev server setup.\n- Build single-page routes.\n- Render responsive modern styled panels.",
    files_schema="package.json, src/App.tsx, src/main.tsx, index.html, Dockerfile",
    key_deps=["react", "react-dom", "typescript", "vite"]
)

DEFAULT_BACKEND = BackendConfig(
    name="FastAPI",
    language="python",
    prompt_guidelines="- Fast web routes using type hints.\n- Include Swagger UI route auto-documentation.\n- Set up CORS middleware.",
    files_schema="main.py, requirements.txt, Dockerfile",
    key_deps=["fastapi", "uvicorn", "pydantic"]
)

DEFAULT_ARCH = ArchitectureConfig(
    name="Monolithic",
    prompt_guidelines="- Single codebase layout structure.\n- Organised subdirectories for separation of concerns."
)


# Standard definitions for frontend options
FRONTEND_REGISTRY: Dict[str, FrontendConfig] = {
    "react": FrontendConfig(
        name="React",
        prompt_guidelines="Use React 18 with TypeScript and Vite. Use React Router v6 for routing. Style with Tailwind CSS.",
        files_schema="package.json, vite.config.ts, src/App.tsx, src/main.tsx, src/pages/Dashboard.tsx, Dockerfile",
        key_deps=["react", "react-dom", "react-router-dom", "lucide-react"]
    ),
    "next.js": FrontendConfig(
        name="Next.js",
        prompt_guidelines="Use Next.js App Router (React 18). Implement folder-based routing with app/page.tsx, app/layout.tsx. Style with CSS Modules or Tailwind.",
        files_schema="package.json, next.config.js, app/page.tsx, app/layout.tsx, app/dashboard/page.tsx, Dockerfile",
        key_deps=["next", "react", "react-dom", "tailwindcss"]
    ),
    "vue.js": FrontendConfig(
        name="Vue.js",
        prompt_guidelines="Use Vue 3 with Composition API (<script setup>). Style with Tailwind CSS. Use Pinia for state if needed.",
        files_schema="package.json, vite.config.ts, src/App.vue, src/main.ts, src/components/Dashboard.vue, Dockerfile",
        key_deps=["vue", "vue-router", "pinia"]
    ),
    "nuxt.js": FrontendConfig(
        name="Nuxt.js",
        prompt_guidelines="Use Nuxt 3 with directories pages/, components/, layouts/. Configure server-side rendering or static generation.",
        files_schema="package.json, nuxt.config.ts, pages/index.vue, pages/dashboard.vue, Dockerfile",
        key_deps=["nuxt", "vue", "vue-router"]
    ),
    "angular": FrontendConfig(
        name="Angular",
        prompt_guidelines="Use Angular CLI project layout. Create standalone components, services, and routing modules.",
        files_schema="package.json, tsconfig.json, src/app/app.component.ts, src/app/app.config.ts, Dockerfile",
        key_deps=["@angular/core", "@angular/common", "@angular/router", "rxjs"]
    ),
    "svelte": FrontendConfig(
        name="Svelte",
        prompt_guidelines="Use Svelte 4 with Vite. Implement stores for reactive state variables. Style inside style blocks in Svelte components.",
        files_schema="package.json, vite.config.ts, src/App.svelte, src/main.ts, Dockerfile",
        key_deps=["svelte", "vite", "typescript"]
    ),
    "sveltekit": FrontendConfig(
        name="SvelteKit",
        prompt_guidelines="Use SvelteKit with routing based on src/routes/+page.svelte. Include +layout.svelte for shared shells.",
        files_schema="package.json, svelte.config.js, src/routes/+page.svelte, src/routes/+layout.svelte, Dockerfile",
        key_deps=["@sveltejs/kit", "svelte", "vite"]
    ),
    "htmx": FrontendConfig(
        name="HTMX",
        prompt_guidelines="Use HTMX attribute extensions (hx-get, hx-post, hx-target, hx-swap). Rely on server-rendered HTML snippets rather than JSON APIs.",
        files_schema="index.html, css/style.css, js/htmx.min.js, Dockerfile",
        key_deps=["htmx.org"]
    ),
    "basic html/css/js": FrontendConfig(
        name="Basic HTML/CSS/JS",
        prompt_guidelines="Use standard semantic HTML5 structures, vanilla CSS style declarations, and browser JS DOM manipulation.",
        files_schema="index.html, styles.css, app.js, Dockerfile",
        key_deps=[]
    ),
    "vanilla javascript": FrontendConfig(
        name="Vanilla JavaScript",
        prompt_guidelines="Create a modern single-page structure using Vanilla JS DOM rendering, dynamic import states, and router classes.",
        files_schema="index.html, src/index.js, src/router.js, Dockerfile",
        key_deps=[]
    ),
    "react native": FrontendConfig(
        name="React Native",
        prompt_guidelines="Use React Native CLI structure. Focus on building reusable native elements, hooks, and native navigation routers.",
        files_schema="package.json, App.tsx, index.js, package-lock.json",
        key_deps=["react", "react-native", "@react-navigation/native"]
    ),
    "flutter web": FrontendConfig(
        name="Flutter Web",
        prompt_guidelines="Use Flutter Dart web module. Generate pubspec.yaml and standard widgets trees (Material/Cupertino).",
        files_schema="pubspec.yaml, web/index.html, lib/main.dart, lib/screens/home.dart, Dockerfile",
        key_deps=["flutter"]
    )
}


# Standard definitions for backend frameworks
BACKEND_REGISTRY: Dict[str, BackendConfig] = {
    "python (fastapi)": BackendConfig(
        name="Python (FastAPI)",
        language="python",
        prompt_guidelines="Use FastAPI 0.111+ with Pydantic v2 schemas and SQLAlchemy 2.x ORM models. Include Swagger routing endpoints.",
        files_schema="main.py, routers/users.py, schemas/user.py, database.py, requirements.txt, Dockerfile",
        key_deps=["fastapi", "uvicorn", "pydantic", "sqlalchemy", "alembic", "psycopg2-binary"]
    ),
    "node.js (express)": BackendConfig(
        name="Node.js (Express)",
        language="javascript",
        prompt_guidelines="Use Node.js with Express router middleware. Structure files into routes/, controllers/, and models/. Use mongoose or pg/sequelize.",
        files_schema="package.json, app.js, routes/api.js, controllers/userController.js, models/index.js, Dockerfile",
        key_deps=["express", "cors", "dotenv", "sequelize", "pg", "jsonwebtoken"]
    ),
    "nestjs": BackendConfig(
        name="NestJS",
        language="typescript",
        prompt_guidelines="Use NestJS architecture with Modules, Controllers, Services, and TypeORM / Prisma ORM integrations.",
        files_schema="package.json, src/main.ts, src/app.module.ts, src/user/user.controller.ts, src/user/user.service.ts, Dockerfile",
        key_deps=["@nestjs/core", "@nestjs/common", "reflect-metadata", "rxjs", "prisma"]
    ),
    "python (django)": BackendConfig(
        name="Python (Django)",
        language="python",
        prompt_guidelines="Use Django REST Framework (DRF) setup. Create a standard Django app structure with settings.py, urls.py, models.py, and serializers.py.",
        files_schema="manage.py, config/settings.py, config/urls.py, api/models.py, api/views.py, api/serializers.py, requirements.txt, Dockerfile",
        key_deps=["django", "djangorestframework", "psycopg2-binary", "django-cors-headers"]
    ),
    "python (flask)": BackendConfig(
        name="Python (Flask)",
        language="python",
        prompt_guidelines="Use Flask micro-framework. Include Flask-SQLAlchemy, Flask-Migrate, and Flask-CORS integrations.",
        files_schema="app.py, models.py, routes.py, config.py, requirements.txt, Dockerfile",
        key_deps=["flask", "flask-sqlalchemy", "flask-migrate", "flask-cors"]
    ),
    "java (spring boot)": BackendConfig(
        name="Java (Spring Boot)",
        language="java",
        prompt_guidelines="Use Spring Boot framework with Maven/Gradle. Structure into controllers, services, repositories, and entity modules using JPA/Hibernate.",
        files_schema="pom.xml, src/main/java/com/app/Application.java, src/main/java/com/app/controller/UserController.java, Dockerfile",
        key_deps=["spring-boot-starter-web", "spring-boot-starter-data-jpa", "postgresql"]
    ),
    "go (gin)": BackendConfig(
        name="Go (Gin)",
        language="go",
        prompt_guidelines="Use Go Gin routing engine. Structure files into main.go, controllers/, models/, and config/. Use GORM for DB operations.",
        files_schema="go.mod, main.go, controllers/user.go, models/user.go, config/db.go, Dockerfile",
        key_deps=["github.com/gin-gonic/gin", "gorm.io/gorm", "gorm.io/driver/postgres"]
    ),
    "go (fiber)": BackendConfig(
        name="Go (Fiber)",
        language="go",
        prompt_guidelines="Use Go Fiber routing engine. Build modular routes and services. Integrate with Postgres using pgx or GORM.",
        files_schema="go.mod, main.go, handlers/user.go, database/db.go, Dockerfile",
        key_deps=["github.com/gofiber/fiber/v2", "gorm.io/gorm"]
    ),
    "rust (actix web)": BackendConfig(
        name="Rust (Actix Web)",
        language="rust",
        prompt_guidelines="Use Actix Web with Cargo dependency setup. Include SQLx ORM structures and serde JSON serialization.",
        files_schema="Cargo.toml, src/main.rs, src/routes/mod.rs, src/models.rs, Dockerfile",
        key_deps=["actix-web", "serde", "tokio", "sqlx"]
    ),
    "rust (axum)": BackendConfig(
        name="Rust (Axum)",
        language="rust",
        prompt_guidelines="Use Axum routing library. Structure routes with handlers and services. Integrate database connections using SQLx or SeaORM.",
        files_schema="Cargo.toml, src/main.rs, src/handlers.rs, src/db.rs, Dockerfile",
        key_deps=["axum", "tokio", "serde", "sqlx"]
    ),
    "php (laravel)": BackendConfig(
        name="PHP (Laravel)",
        language="php",
        prompt_guidelines="Use Laravel framework setup. Structure models with Eloquent relations and controllers inside App\\Http\\Controllers.",
        files_schema="composer.json, artisan, routes/api.php, app/Http/Controllers/UserController.php, app/Models/User.php, Dockerfile",
        key_deps=["laravel/framework", "lucidarch/lucid"]
    ),
    "elixir (phoenix)": BackendConfig(
        name="Elixir (Phoenix)",
        language="elixir",
        prompt_guidelines="Use Phoenix MVC layout. Generate controllers, router.ex, schemas, and queries using Ecto database adapter.",
        files_schema="mix.exs, lib/app_web/router.ex, lib/app_web/controllers/user_controller.ex, Dockerfile",
        key_deps=["phoenix", "phoenix_ecto", "ecto_sql", "postgrex"]
    ),
    "grpc services": BackendConfig(
        name="gRPC Services",
        language="protobuf",
        prompt_guidelines="Define gRPC services in proto3 files. Implement gRPC server handlers in Python or Go.",
        files_schema="protos/service.proto, server.go, client_example.go, Dockerfile",
        key_deps=["google.golang.org/grpc", "google.golang.org/protobuf"]
    )
}


# Standard definitions for architectures
ARCH_REGISTRY: Dict[str, ArchitectureConfig] = {
    "monolithic": ArchitectureConfig(
        name="Monolithic",
        prompt_guidelines="Organise all code into a single executable service with folders: frontend/ and backend/."
    ),
    "modular monolith": ArchitectureConfig(
        name="Modular Monolith",
        prompt_guidelines="Organise application into clear, self-contained business modules (e.g. users/, orders/) within a single deployable repository. Communication between modules must happen through clean local interfaces/events rather than direct imports."
    ),
    "microservices": ArchitectureConfig(
        name="Microservices",
        prompt_guidelines="Decouple logic into separate backend service containers. Include a docker-compose.yml file linking services, and define API routes communicating via REST or gRPC."
    ),
    "event-driven architecture": ArchitectureConfig(
        name="Event-Driven Architecture",
        prompt_guidelines="Use an event broker abstraction. Structure services around events, publishing events (e.g., UserCreated) to a bus and setting up subscription listeners."
    ),
    "serverless": ArchitectureConfig(
        name="Serverless",
        prompt_guidelines="Organise backend endpoints as isolated handler functions suitable for AWS Lambda, Google Cloud Functions, or Vercel Serverless. Avoid long-running server loops."
    ),
    "hexagonal architecture (ports & adapters)": ArchitectureConfig(
        name="Hexagonal Architecture (Ports & Adapters)",
        prompt_guidelines="Structure the backend with three strict directories:\n- core/domain/ (entities and models)\n- core/ports/ (interfaces for database, authentication, etc.)\n- adapters/ (implementations like REST API handlers, SQL database adapters, etc.)"
    ),
    "clean architecture": ArchitectureConfig(
        name="Clean Architecture",
        prompt_guidelines="Enforce dependency layers flowing inwards:\n- Domain layer (entities, rules)\n- Use Cases layer (business actions)\n- Interface Adapters (controllers, gateways)\n- External Frameworks (express/fastapi, database drivers)\nStrictly avoid importing outer layers in inner layers."
    ),
    "onion architecture": ArchitectureConfig(
        name="Onion Architecture",
        prompt_guidelines="Enforce concentric dependency circles. Put Domain Model in the center, Domain Services around it, Application Services next, and Infrastructure (databases, UI) at the outermost circle."
    ),
    "cqrs": ArchitectureConfig(
        name="CQRS",
        prompt_guidelines="Separate database write operations (Commands) from read operations (Queries) into completely distinct paths, handlers, or database models. Do not mix read and write logic."
    ),
    "domain-driven design (ddd)": ArchitectureConfig(
        name="Domain-Driven Design (DDD)",
        prompt_guidelines="Structure around Bounded Contexts. Put Aggregate Roots, Value Objects, Domain Events, and Repositories in explicit context boundaries."
    )
}


# ── Registry Lookup Helpers ───────────────────────────────────────────────────

def get_frontend_config(frontend_name: str) -> FrontendConfig:
    """Look up configuration for a frontend framework option (case-insensitive fallback)."""
    key = frontend_name.strip().lower()
    if key in FRONTEND_REGISTRY:
        return FRONTEND_REGISTRY[key]
    
    # Check prefixes
    for k, cfg in FRONTEND_REGISTRY.items():
        if k in key or key in k:
            return cfg

    # Dynamic default generator
    return FrontendConfig(
        name=frontend_name,
        prompt_guidelines=f"- Structure files matching {frontend_name} standard layout.\n- Generate clean configuration and boilerplate files.\n- Use the standard styles framework selected.",
        files_schema="package.json, src/index, index.html, Dockerfile",
        key_deps=[frontend_name.lower().split()[0]]
    )


def get_backend_config(backend_name: str) -> BackendConfig:
    """Look up configuration for a backend framework option (case-insensitive fallback)."""
    key = backend_name.strip().lower()
    if key in BACKEND_REGISTRY:
        return BACKEND_REGISTRY[key]

    for k, cfg in BACKEND_REGISTRY.items():
        if k in key or key in k:
            return cfg

    # Infer language from backend_name
    language = "javascript"
    if "python" in key or "django" in key or "flask" in key or "fastapi" in key or "tornado" in key:
        language = "python"
    elif "go" in key or "gin" in key or "fiber" in key or "echo" in key:
        language = "go"
    elif "java" in key or "spring" in key or "quarkus" in key:
        language = "java"
    elif "rust" in key or "actix" in key or "axum" in key:
        language = "rust"
    elif "php" in key or "laravel" in key or "symfony" in key:
        language = "php"
    elif "elixir" in key or "phoenix" in key:
        language = "elixir"
    elif "kotlin" in key or "ktor" in key:
        language = "kotlin"

    # Map files list
    files_schema = "main.py, requirements.txt, Dockerfile"
    if language == "javascript" or language == "typescript":
        files_schema = "package.json, app.js, Dockerfile"
    elif language == "go":
        files_schema = "go.mod, main.go, Dockerfile"
    elif language == "rust":
        files_schema = "Cargo.toml, src/main.rs, Dockerfile"
    elif language == "php":
        files_schema = "composer.json, index.php, Dockerfile"

    return BackendConfig(
        name=backend_name,
        language=language,
        prompt_guidelines=f"- Generate clean {backend_name} backend code.\n- Implement secure routing API endpoints.\n- Structure folders by separation of concerns.",
        files_schema=files_schema,
        key_deps=[backend_name.lower().split()[0]]
    )


def get_architecture_config(arch_name: str) -> ArchitectureConfig:
    """Look up configuration for an architecture pattern option (case-insensitive fallback)."""
    key = arch_name.strip().lower()
    if key in ARCH_REGISTRY:
        return ARCH_REGISTRY[key]

    for k, cfg in ARCH_REGISTRY.items():
        if k in key or key in k:
            return cfg

    return ArchitectureConfig(
        name=arch_name,
        prompt_guidelines=f"- Follow the clean {arch_name} software architecture pattern.\n- Organise directories and modules accordingly."
    )
