# Domain Requirements Template

Use this template when creating `domain-requirements.md` in Phase 1, Step 1.

---

## Template

```markdown
# Domain Requirements: <Feature Name>

## Problem Statement
[Clear description of the business problem being solved]

## Users & Personas
[Who will use this feature, their roles and characteristics]

## Business Objectives
[What business outcomes we're trying to achieve]

## Success Metrics
[How we'll measure success - specific, measurable criteria]

## Functional Requirements

### Core Functionality
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

### User Workflows
1. [Workflow 1: Name and brief description]
2. [Workflow 2: Name and brief description]

### Business Rules
- [Rule 1]
- [Rule 2]

## Non-Functional Requirements
- **Performance:** [Load times, response times, throughput]
- **Platform:** [Web / Mobile / Both]
- **Offline:** [Yes/No, sync requirements]
- **Security:** [Data privacy, authentication requirements]
- **Accessibility:** [WCAG level, specific requirements]

## Constraints & Dependencies
- **Technical:** [API limits, hardware limitations]
- **Dependencies:** [Other features, external APIs]
- **Timeline:** [Deadlines, milestones]
- **Budget:** [Resource limitations]

## User Experience Requirements
- **Discovery:** [How users find this feature]
- **Journey:** [Step-by-step user flow]
- **Feedback:** [Toasts, dialogs, progress indicators]
- **Error handling:** [Error scenarios and messaging]
```

---

## Gathering Requirements

Use **AskUserQuestion** at every step to clarify:

### 1. Problem & User Understanding
- What business problem are we solving?
- Who are the users? (roles, personas, skill levels)
- What pain points do users currently experience?
- What outcomes do users expect?

### 2. Business Context
- What are the business objectives?
- What success metrics will we track?
- What's the priority/urgency? (P0/P1/P2)

### 3. Functional Requirements
- What core functionality must the feature provide?
- What are the main user workflows?
- What data needs CRUD operations?

### 4. Non-Functional Requirements
- Performance expectations?
- Offline/online requirements?
- Multi-platform needs?
- Security concerns?

### 5. Constraints & Dependencies
- Technical constraints?
- Integration requirements?
- Dependencies on other features?

### 6. User Experience
- How should users discover this feature?
- What error scenarios need handling?
- What feedback should users receive?

---

**Key Principle:** NO assumptions. Ask clarifying questions at every step.
