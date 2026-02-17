# Agent Prompt Templates

Reusable prompt templates for discovery and research agents.

---

## Explore Agent Prompts

### Similar Features Search

```
Find existing features similar to {feature-name}. Look for:
- Similar UI screens or pages (same problem domain)
- Similar state management patterns (ViewModels, providers, controllers)
- Similar data flows (entity management, CRUD operations)
- File naming conventions for similar features
- Directory organization patterns

Provide specific file paths and examples of patterns found.
```

**Variables to fill:**
- `{feature-name}` - Name or description of feature being planned

**Example:**
```
Find existing features similar to notification system. Look for:
- Similar UI screens or pages (alerts, messages, status indicators)
- Similar state management patterns (ViewModels, providers, controllers)
- Similar data flows (push notifications, in-app alerts)
- File naming conventions for similar features
- Directory organization patterns

Provide specific file paths and examples of patterns found.
```

---

### Project Structure Discovery

```
Explore current project structure to understand conventions. Find:

1. Where providers are located:
   - Search for all *provider*.dart files
   - Show directory paths and organization
   - Identify naming patterns

2. Where state classes are located:
   - Search for *state*.dart files
   - Search for files with Freezed/state classes
   - Show where entity states vs page states live

3. Where controllers/ViewModels are located:
   - Search for *controller*.dart files
   - Search for *view_model*.dart files
   - Show directory structure

4. Directory structure in lib/data/ and lib/ui/:
   - List directories and their purposes
   - Identify feature organization patterns
   - Find examples of feature folders

Provide specific examples with file paths.
```

**No variables needed** - This prompt is self-contained

---

### State Management Pattern Discovery

```
Find existing state management patterns in the codebase. Look for:

1. Riverpod usage:
   - Files using @riverpod annotation
   - ConsumerWidget/ConsumerStatefulWidget examples
   - Provider types used (StateNotifier, AsyncNotifier, FutureProvider, etc.)
   - Code generation patterns (*.g.dart files)

2. Provider (ChangeNotifier) usage:
   - Files extending ChangeNotifier
   - ChangeNotifierProvider usage
   - Listener patterns

3. State class patterns:
   - Freezed usage (@freezed annotation)
   - Manual immutable classes
   - State class organization (separate files vs same file as provider)

4. Existing provider examples:
   - Show 2-3 complete examples of provider implementations
   - Include file paths and patterns

Provide code examples showing the patterns.
```

**No variables needed** - This prompt is self-contained

---

### Reusable Components Discovery

```
Find reusable components relevant to {feature-name}. Look for:

1. UI Components:
   - Widgets in lib/ui/components/ or lib/ui/shared/
   - Common UI patterns (buttons, dialogs, forms)
   - Layout components

2. Service Classes:
   - Services in lib/data/services/
   - API clients
   - Business logic helpers

3. Utility Functions:
   - Utilities in lib/utils/ or lib/helpers/
   - Extensions
   - Common functions

4. Existing Integrations:
   - Third-party package usage
   - Firebase integrations
   - Platform-specific code

Provide file paths and brief descriptions of what each component does.
```

**Variables to fill:**
- `{feature-name}` - Feature being planned

**Example:**
```
Find reusable components relevant to notification system. Look for:
[same structure as above]
```

---

### Naming Convention Discovery

```
Analyze naming conventions in the codebase. Find:

1. File naming patterns:
   - Providers: {name}_provider.dart vs provider_{name}.dart?
   - States: {name}_state.dart vs state_{name}.dart?
   - Screens: {name}_screen.dart vs {name}_page.dart?
   - Widgets: {name}_widget.dart or just {name}.dart?

2. Class naming patterns:
   - Providers: {Name}Provider vs {Name}Notifier?
   - States: {Name}State vs {Name}?
   - Screens: {Name}Screen vs {Name}Page?

3. Directory naming:
   - snake_case vs camelCase vs kebab-case?
   - Singular vs plural names?

Provide examples from actual codebase files.
```

**No variables needed** - Analyzes existing patterns

---

### Database Layer Discovery

```
Find existing database access patterns for {entity-name}. Look for:

1. Database Wrappers:
   - Files in lib/data/daos/
   - {Entity}Db.instance pattern
   - Available CRUD methods

2. Models:
   - Base models in lib/data/models/base_models/
   - SQLite models in lib/data/models/sqlite/
   - Firestore models in lib/data/models/firestore/

3. Usage Examples:
   - Where {entity} data is accessed
   - How inserts/updates are performed
   - Query patterns

Provide file paths and code examples.
```

**Variables to fill:**
- `{entity-name}` - Entity/model being used (e.g., "Athlete", "Workout")

**Example:**
```
Find existing database access patterns for Athlete. Look for:
[same structure]
```

---

## Web Search Researcher Prompts

### Flutter Best Practices Research

```
Research current Flutter best practices for {topic} in 2026.
Focus on:
- {Specific aspect 1}
- {Specific aspect 2}
- {Specific aspect 3}

Compare with our current pattern: {discovered_pattern}

Provide recommendations with pros/cons for each approach.
Include code examples where relevant.
```

**Variables to fill:**
- `{topic}` - Topic to research (e.g., "state management", "navigation", "form handling")
- `{Specific aspect 1-3}` - Specific areas of interest
- `{discovered_pattern}` - Current pattern found in codebase

**Example:**
```
Research current Flutter best practices for state management in 2026.
Focus on:
- Riverpod 3.x best practices
- Code generation with riverpod_generator
- State class patterns with Freezed
- Performance optimization

Compare with our current pattern: @riverpod annotation with StateProvider

Provide recommendations with pros/cons for each approach.
Include code examples where relevant.
```

---

### Package/Library Research

```
Research {package-name} for use in {feature-description}.

Find:
1. Current version and stability (2026)
2. Integration with Flutter {flutter-version}
3. Common usage patterns and examples
4. Pros and cons compared to alternatives
5. Known issues or limitations
6. Best practices for implementation

Provide setup instructions and code examples.
```

**Variables to fill:**
- `{package-name}` - Package to research
- `{feature-description}` - What it will be used for
- `{flutter-version}` - Current Flutter version

**Example:**
```
Research firebase_messaging for use in push notification system.

Find:
1. Current version and stability (2026)
2. Integration with Flutter 3.35.3
3. Common usage patterns and examples
4. Pros and cons compared to alternatives (OneSignal, Pusher)
5. Known issues or limitations
6. Best practices for implementation

Provide setup instructions and code examples.
```

---

### Architecture Pattern Research

```
Research architectural patterns for {feature-type} in Flutter (2026).

Compare:
1. {Approach 1}: {brief description}
2. {Approach 2}: {brief description}
3. {Approach 3}: {brief description}

For each approach, provide:
- Use cases (when to use)
- Pros and cons
- Code structure example
- Integration effort
- Community adoption

Recommend which approach fits best for {project-context}.
```

**Variables to fill:**
- `{feature-type}` - Type of feature (e.g., "real-time notifications", "offline-first data sync")
- `{Approach 1-3}` - Different approaches to compare
- `{project-context}` - Project-specific context

**Example:**
```
Research architectural patterns for real-time notifications in Flutter (2026).

Compare:
1. Stream-based: StreamProvider with Firebase Firestore snapshots
2. Polling: Periodic API calls with Timer
3. WebSocket: Direct WebSocket connection with custom protocol

For each approach, provide:
- Use cases (when to use)
- Pros and cons
- Code structure example
- Integration effort
- Community adoption

Recommend which approach fits best for offline-first mobile app with Firebase backend.
```

---

## Codebase Pattern Finder Prompts

### Existing Pattern Examples

```
Find examples of {pattern-type} in the codebase.

Look for:
1. Complete implementations (not fragments)
2. Recent code (not deprecated patterns)
3. Well-structured examples to model after

Show 2-3 examples with:
- File path
- Complete code (not excerpts)
- Explanation of pattern used
- Why this is a good example
```

**Variables to fill:**
- `{pattern-type}` - Type of pattern (e.g., "form validation", "list pagination", "error handling")

**Example:**
```
Find examples of form validation in the codebase.

Look for:
1. Complete implementations (not fragments)
2. Recent code (not deprecated patterns)
3. Well-structured examples to model after

Show 2-3 examples with:
- File path
- Complete code
- Explanation of pattern used
- Why this is a good example
```

---

### Anti-Pattern Detection

```
Search for potential anti-patterns related to {feature-area}.

Look for:
1. Code that violates project conventions
2. Deprecated patterns still in use
3. Performance issues
4. Common mistakes

For each finding:
- File path
- Code snippet
- Why it's problematic
- Recommended fix
```

**Variables to fill:**
- `{feature-area}` - Area to analyze (e.g., "state management", "database access", "navigation")

**Example:**
```
Search for potential anti-patterns related to database access.

Look for:
1. Direct DAO imports (should use wrappers)
2. Missing userId/orgId filters
3. Synchronous Firestore calls
4. Bypassed platform detection

For each finding:
- File path
- Code snippet
- Why it's problematic
- Recommended fix
```

---

## Prompt Usage Guidelines

### When to Use Explore Agent
- Open-ended codebase discovery
- Finding patterns and conventions
- Locating similar features
- Understanding project structure

**Characteristics:**
- Requires searching multiple locations
- Pattern matching across files
- Structural analysis
- No specific file path known

---

### When to Use Web Search Researcher
- External best practices
- Package/library research
- Comparing architectural approaches
- Industry standards and trends
- New technologies not in codebase

**Characteristics:**
- Information not in codebase
- Need current (2026) practices
- Comparing alternatives
- Learning new patterns

---

### When to Use Codebase Pattern Finder
- Finding specific code examples
- Locating existing implementations
- Identifying anti-patterns
- Code quality analysis

**Characteristics:**
- Know roughly what to look for
- Need actual code examples
- Want to model after existing code
- Quality assessment

---

## Combining Prompts

### Sequential Discovery
```
Step 1: Use "Project Structure Discovery"
   |
Step 2: Use "State Management Pattern Discovery"
   |
Step 3: Use "Similar Features Search" with structure context
   |
Step 4: Present findings to user
```

### Parallel Discovery
```
Launch simultaneously:
- "Similar Features Search"
- "Project Structure Discovery"
- "State Management Pattern Discovery"

Wait for all results, then aggregate and present.
```

---

## Customizing Prompts

### Adding Project-Specific Details
```
// Generic
"Find state management patterns"

// Customized for SpeedTrap Cloud
"Find state management patterns in SpeedTrap Cloud codebase.
Note: Project uses hybrid architecture with SQLite + Firestore.
Focus on patterns that work offline-first."
```

### Focusing the Search
```
// Too broad
"Find UI components"

// Focused
"Find reusable UI components in lib/ui/components/
specifically for displaying athlete data (lists, cards, detail views)"
```

### Requesting Specific Output Format
```
// Vague
"Find providers"

// Specific format
"Find all provider files and output in table format:
| File Path | Provider Name | State Type | Pattern (Riverpod/ChangeNotifier) |"
```

---

## Prompt Testing Tips

1. **Test prompts incrementally** - Start with one discovery task, refine, then move to next
2. **Check output quality** - Ensure file paths are real, code examples are complete
3. **Adjust specificity** - Too vague = no results; too specific = missed patterns
4. **Iterate based on results** - If discovery misses something, refine prompt and re-run
5. **Validate findings** - Spot-check a few file paths to ensure accuracy

---

## Related References

- [discovery-process.md](discovery-process.md) - Complete discovery workflow
- [examples.md](examples.md) - Real discovery examples with prompts and results
