"""Prompts and LLM schemas for SkillForce curriculum planner (agent 5)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .prereqs import normalize_skill_name

SYSTEM_PROMPT = (
    "You are a curriculum designer. Write one concrete, buildable mini-project and three short practice tasks for "
    "the given skill and target level. Keep them achievable in a few hours. Output ONLY JSON matching the schema."
)


class StepPlan(BaseModel):
    """Schema returned by call_llm for a roadmap step's mini-project and practice tasks."""

    mini_project: str = Field(description="A concrete, one-line buildable mini-project.")
    practice_tasks: list[str] = Field(
        min_length=3,
        max_length=3,
        description="Three short practice tasks achievable in a few hours.",
    )


def build_user_prompt(skill: str, target_level: int, is_revision: bool = False) -> str:
    """Build the user prompt for call_llm."""
    if is_revision:
        return (
            f"Write a refresher mini-project and 3 practice tasks for {skill} focusing on fundamental weak "
            f"sub-topics, edge cases, and core patterns at level {target_level}."
        )
    return (
        f"Write a concrete, buildable mini-project and 3 practice tasks for {skill} at target level {target_level}."
    )


_MOCK_PLANS: dict[str, tuple[dict[str, object], dict[str, object]]] = {
    # skill: (main_step_mock, revision_step_mock)
    "javascript": (
        {
            "mini_project": "Build an interactive task dashboard with local storage persistence and event delegation.",
            "practice_tasks": [
                "Implement DOM manipulation and event handlers for interactive task filtering.",
                "Manage asynchronous data fetching with fetch and async/await.",
                "Structure modular JavaScript functions with clean error handling.",
            ],
        },
        {
            "mini_project": "Build a mini async utility library implementing debounce, throttle, and event emitters.",
            "practice_tasks": [
                "Implement and test JavaScript closures, lexical scope, and state retention.",
                "Refactor nested callbacks into clean Promise chains and async/await flows.",
                "Debug common prototype inheritance and 'this' binding edge cases.",
            ],
        },
    ),
    "react": (
        {
            "mini_project": "Build a responsive product catalogue with client-side filtering and custom hooks.",
            "practice_tasks": [
                "Create reusable UI components with typed props and composite layouts.",
                "Implement stateful forms and client-side state using useState and useReducer.",
                "Fetch and display remote API data with useEffect and loading states.",
            ],
        },
        {
            "mini_project": "Build an interactive dashboard testing component lifecycle and state re-renders.",
            "practice_tasks": [
                "Audit and fix missing dependencies in useEffect and useCallback hooks.",
                "Refactor deeply nested prop drilling to React Context and custom hooks.",
                "Diagnose and eliminate unnecessary component re-renders with React.memo.",
            ],
        },
    ),
    "node.js": (
        {
            "mini_project": "Build a modular RESTful API service with route handlers, middleware, and JSON validation.",
            "practice_tasks": [
                "Set up an HTTP server and configure modular Express route controllers.",
                "Implement request validation and global error-handling middleware.",
                "Write automated integration tests for CRUD endpoints with Supertest.",
            ],
        },
        {
            "mini_project": "Build an event-driven file processing stream with robust error recovery.",
            "practice_tasks": [
                "Diagnose Node.js event loop blocking and non-blocking I/O execution order.",
                "Handle stream backpressure and uncaught promise rejections safely.",
                "Implement structured asynchronous logging with correlation IDs.",
            ],
        },
    ),
    "python": (
        {
            "mini_project": "Build a modular CLI utility with argument parsing, file processing, and logging.",
            "practice_tasks": [
                "Write modular functions with explicit type hints and unit tests.",
                "Parse, transform, and output structured JSON and CSV data files.",
                "Implement custom exceptions and structured logging for error cases.",
            ],
        },
        {
            "mini_project": "Build an in-memory data cache implementing Python decorators and generator pipelines.",
            "practice_tasks": [
                "Create custom function decorators with wraps and argument preservation.",
                "Build memory-efficient streaming data pipelines using generator expressions.",
                "Debug mutable default argument traps and object reference aliasing.",
            ],
        },
    ),
    "sql": (
        {
            "mini_project": "Design an e-commerce database schema and write analytical aggregation queries.",
            "practice_tasks": [
                "Define normalized tables with primary keys, foreign keys, and unique constraints.",
                "Write multi-table INNER and LEFT JOIN queries with grouped aggregations.",
                "Implement window functions to compute running totals and category rankings.",
            ],
        },
        {
            "mini_project": "Refactor slow database queries and resolve NULL-handling edge cases.",
            "practice_tasks": [
                "Audit three-valued logic and correct subtle NULL comparison issues in WHERE clauses.",
                "Rewrite correlated subqueries into clean Common Table Expressions (CTEs).",
                "Analyze query execution plans and add targeted B-tree indexes.",
            ],
        },
    ),
    "html": (
        {
            "mini_project": "Build an accessible, responsive multi-section landing page with semantic markup.",
            "practice_tasks": [
                "Structure page content using semantic HTML5 landmark tags (header, nav, main, footer).",
                "Create accessible web forms with associated labels, fieldsets, and validation attributes.",
                "Verify keyboard navigation and ARIA roles for screen reader compliance.",
            ],
        },
        {
            "mini_project": "Audit and remediate an inaccessible web form to meet WCAG 2.1 AA standards.",
            "practice_tasks": [
                "Fix missing form control labels, aria-describedby hints, and error announcements.",
                "Ensure proper document heading hierarchy and landmark region navigation.",
                "Validate accessible contrast and focus visible indicators across interactive elements.",
            ],
        },
    ),
    "css": (
        {
            "mini_project": "Build a responsive mobile-first landing page using modern Flexbox and Grid layouts.",
            "practice_tasks": [
                "Create a two-dimensional responsive dashboard layout using CSS Grid.",
                "Design a flexible navigation bar and responsive card gallery with Flexbox.",
                "Implement CSS custom properties for cohesive theming and light/dark modes.",
            ],
        },
        {
            "mini_project": "Refactor legacy stylesheet rules to resolve specificity conflicts and layout bugs.",
            "practice_tasks": [
                "Eliminate !important overrides by restructuring selector specificity.",
                "Fix CSS box model padding and border sizing causing horizontal scrollbars.",
                "Resolve mobile responsive breakpoint overflows and layout shifts.",
            ],
        },
    ),
    "pandas": (
        {
            "mini_project": "Build an automated data cleaning and summary report pipeline for sales transactions.",
            "practice_tasks": [
                "Load datasets from CSV/Parquet and inspect schema data types and null counts.",
                "Filter, group, and aggregate multidimensional metrics using groupby and agg.",
                "Reshape and merge multiple tables with merge and pivot_table.",
            ],
        },
        {
            "mini_project": "Diagnose and fix performance bottlenecks and chained assignment warnings in Pandas.",
            "practice_tasks": [
                "Resolve SettingWithCopyWarning by using explicit .loc indexing.",
                "Handle missing data and imputations across categorical and numerical columns.",
                "Vectorize string and date operations to avoid slow row-by-row iterrows loops.",
            ],
        },
    ),
    "docker": (
        {
            "mini_project": "Containerize a multi-service web application using Docker and Docker Compose.",
            "practice_tasks": [
                "Write an optimized multi-stage Dockerfile with minimal image layer size.",
                "Configure Docker Compose for web, worker, and database service orchestration.",
                "Manage persistent data storage using named Docker volumes and health checks.",
            ],
        },
        {
            "mini_project": "Audit and harden container security and resolve permission and caching issues.",
            "practice_tasks": [
                "Configure non-root user execution inside container images.",
                "Optimize Docker build cache ordering for fast, repeatable CI builds.",
                "Debug container networking, port mapping, and DNS resolution issues.",
            ],
        },
    ),
}


def get_mock_step_plan(skill: str, target_level: int, is_revision: bool = False) -> StepPlan:
    """Return a deterministic, valid StepPlan mock for offline mode (USE_MOCK_LLM=1)."""
    norm = normalize_skill_name(skill)
    if norm in _MOCK_PLANS:
        main_dict, rev_dict = _MOCK_PLANS[norm]
        data = rev_dict if is_revision else main_dict
        return StepPlan.model_validate(data)

    # Clean fallback for any skill
    if is_revision:
        return StepPlan(
            mini_project=f"Build a focused debugging and revision exercise for {skill} core concepts.",
            practice_tasks=[
                f"Review fundamental syntax, patterns, and principles of {skill}.",
                f"Identify and fix common pitfalls and anti-patterns in {skill}.",
                f"Write unit tests to verify expected behavior for {skill} edge cases.",
            ],
        )

    return StepPlan(
        mini_project=f"Build a practical {skill} project demonstrating level {target_level} capabilities.",
        practice_tasks=[
            f"Implement core functionality using {skill} best practices.",
            f"Add input validation, error handling, and tests in {skill}.",
            f"Document design trade-offs and verify solution readiness for {skill}.",
        ],
    )


__all__ = [
    "SYSTEM_PROMPT",
    "StepPlan",
    "build_user_prompt",
    "get_mock_step_plan",
]
