# Discovery Process Details

Complete guide for the automated discovery phase of feature planning.

---

## Overview

The discovery-first approach uses Explore agents to understand existing patterns before suggesting architecture. This ensures consistency with the actual codebase rather than generic Flutter conventions.

**Benefits:**
- Discover real patterns, not assumed ones
- Find reusable components automatically
- Learn actual naming conventions
- Identify similar features to model after
- Base suggestions on evidence, not guesses

---

## Discovery Task 1: Similar Features

**Purpose:** Find existing features similar to the one being planned

**Agent Prompt Template:**
```
Find existing features similar to {feature-name}. Look for:
- Similar UI screens or pages (same problem domain)
- Similar state management patterns (ViewModels, providers, controllers)
- Similar data flows (entity management, CRUD operations)
- File naming conventions for similar features
- Directory organization patterns

Provide specific file paths and examples of patterns found.
```

**What to Look For:**
- Features solving similar problems
- UI patterns for similar user interactions
- Data management for similar entity types
- Navigation patterns for similar flows

**Example:**
```
User wants: Notification system

Discovery finds:
- lib/ui/sync_status/ - Status notifications in HomePage
- lib/data/providers/hardware_providers.dart - Alert notifications for BLE
- lib/ui/components/toast_messages.dart - Reusable toast component

Patterns found:
- Notifications use SnackBar widget
- Provider pattern with ChangeNotifier
- State stored in provider, UI listens
```

**Output Format:**
```markdown
## Similar Features Found

### Feature 1: Sync Status Notifications
**Location:** lib/ui/home/widgets/sync_status_indicator.dart
**Pattern:** Provider + ChangeNotifier + SnackBar
**State Management:** SyncStatusProvider (lib/data/providers/sync_provider.dart)
**Reusable Components:**
- toast_messages.dart - Toast display logic
- notification_service.dart - Notification coordination

**Key Patterns:**
- Provider notifies listeners on state change
- UI subscribes with Consumer widget
- SnackBar for temporary messages
- Persistent UI indicator for ongoing status

### Feature 2: Hardware Alert System
**Location:** lib/data/providers/hardware_providers.dart
**Pattern:** Riverpod + AlertDialog
**State Management:** HardwareProvider (@riverpod annotation)
**Reusable Components:**
- alert_dialog.dart - Standard alert dialogs
- error_handler.dart - Error notification routing

**Key Patterns:**
- Riverpod with @riverpod annotation
- Modal dialogs for critical alerts
- Error states trigger notifications
- Notification queue for multiple alerts

### Common Patterns Across Features:
- Provider-based state management (ChangeNotifier)
- UI subscriptions with Consumer widgets
- Separate notification service for coordination
- Different UI patterns for different notification types
```

---

## Discovery Task 2: Project Structure Conventions

**Purpose:** Understand where files are located and how they're organized

**Agent Prompt Template:**
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

**What to Look For:**
- Where providers are stored (shared? page-specific?)
- Naming conventions (camelCase? snake_case?)
- Feature folder structure
- Separation between data and UI layers
- State class organization

**Example:**
```
Discovery finds:

Providers:
- lib/data/providers/ - Shared providers (23 files)
  - hardware_providers.dart
  - org_providers.dart
  - auth_providers.dart
- lib/ui/*/providers/ - Page-specific providers (5 files)
  - lib/ui/workouts/providers/workout_form_provider.dart

State Classes:
- lib/data/state/ - Entity states (12 files)
  - athlete_state.dart
  - workout_state.dart
- Inline with providers (11 files)
  - Some providers define state in same file

Controllers/ViewModels:
- NOT FOUND - Project doesn't use controllers
- Uses providers instead

Directory Structure:
lib/
├── data/
│   ├── daos/           - Database wrappers
│   ├── models/         - Data models
│   ├── providers/      - Shared state (23 files)
│   ├── services/       - Business logic
│   └── state/          - Entity state classes
├── ui/
│   ├── components/     - Reusable widgets
│   ├── athletes/       - Feature folder
│   │   ├── screens/
│   │   ├── widgets/
│   │   └── providers/  - Feature-specific providers
│   └── workouts/       - Feature folder
│       ├── screens/
│       └── providers/
```

**Output Format:**
```markdown
## Project Structure Conventions

### Providers
**Primary Location:** lib/data/providers/ (shared across features)
**Secondary Location:** lib/ui/{feature}/providers/ (feature-specific)

**Naming Pattern:** {entity}_provider.dart or {feature}_provider.dart
**Examples:**
- lib/data/providers/hardware_providers.dart (shared)
- lib/data/providers/org_providers.dart (shared)
- lib/ui/workouts/providers/workout_form_provider.dart (feature-specific)

**Organization:**
- Shared providers for app-wide state
- Feature-specific providers colocated with UI

### State Classes
**Primary Location:** lib/data/state/ (entity states)
**Secondary Location:** Inline with provider (some cases)

**Naming Pattern:** {entity}_state.dart
**Examples:**
- lib/data/state/athlete_state.dart
- lib/data/state/workout_state.dart
- lib/data/providers/sync_provider.dart (inline state)

**Organization:**
- Separate files for complex state
- Inline for simple state classes

### Controllers/ViewModels
**Status:** NOT USED in this project
**Alternative:** Providers handle state management and business logic

### Feature Organization
**Pattern:** Feature folders in lib/ui/{feature}/
**Structure:**
```
lib/ui/{feature}/
├── screens/      - Full-page screens
├── widgets/      - Feature-specific widgets
└── providers/    - Feature-specific state (optional)
```

**Examples:**
- lib/ui/athletes/ (screens/, widgets/)
- lib/ui/workouts/ (screens/, widgets/, providers/)
```

---

## Discovery Task 3: State Management Patterns

**Purpose:** Understand which state management approach(es) the project uses

**Agent Prompt Template:**
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

**What to Look For:**
- Which state management library (Riverpod, Provider, Bloc, etc.)
- Code generation usage (@riverpod, @freezed)
- How state classes are structured
- Provider/Notifier patterns
- Real code examples to model after

**Example:**
```
Discovery finds:

Riverpod:
- 23 providers using @riverpod annotation
- Code generation with riverpod_generator
- ConsumerWidget used in 45 files
- Mainly StateProvider and FutureProvider

Provider (ChangeNotifier):
- 5 providers extending ChangeNotifier
- Older code, being migrated to Riverpod
- ChangeNotifierProvider wrappers
- Consumer widget for listening

State Classes:
- 12 files with @freezed annotation
- Freezed for immutable state
- Separate .freezed.dart files
- copyWith() for updates

Example 1: Riverpod with code generation
lib/data/providers/org_providers.dart:
```dart
@riverpod
class CurrentOrg extends _$CurrentOrg {
  @override
  Organization? build() => null;

  void setOrg(Organization org) {
    state = org;
  }
}
```

Example 2: Provider with ChangeNotifier
lib/data/providers/hardware_provider.dart:
```dart
class HardwareProvider extends ChangeNotifier {
  List<BluetoothDevice> _devices = [];

  List<BluetoothDevice> get devices => _devices;

  void addDevice(BluetoothDevice device) {
    _devices.add(device);
    notifyListeners();
  }
}
```

Example 3: Freezed state class
lib/data/state/athlete_state.dart:
```dart
@freezed
class AthleteState with _$AthleteState {
  const factory AthleteState({
    @Default([]) List<Athlete> athletes,
    @Default(false) bool isLoading,
    String? error,
  }) = _AthleteState;
}
```
```

**Output Format:**
```markdown
## State Management Patterns Found

### Riverpod (Primary - 23 providers)
**Status:** Active, preferred approach
**Code Generation:** Yes (riverpod_generator + build_runner)
**Provider Types Used:**
- StateProvider (simple state)
- FutureProvider (async data loading)
- StreamProvider (real-time data)

**Pattern:**
```dart
@riverpod
class FeatureName extends _$FeatureName {
  @override
  StateType build() => initialState;

  void updateState(newValue) {
    state = newValue;
  }
}
```

**Usage in UI:**
```dart
class MyWidget extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(featureNameProvider);
    return Text(state.toString());
  }
}
```

**Files:** lib/data/providers/ (23 files)

### Provider with ChangeNotifier (Legacy - 5 providers)
**Status:** Being migrated to Riverpod
**Code Generation:** No

**Pattern:**
```dart
class FeatureProvider extends ChangeNotifier {
  StateType _state = initialState;

  StateType get state => _state;

  void updateState(newValue) {
    _state = newValue;
    notifyListeners();
  }
}
```

**Usage in UI:**
```dart
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<FeatureProvider>(
      builder: (context, provider, child) {
        return Text(provider.state.toString());
      },
    );
  }
}
```

**Files:** lib/data/providers/ (5 older files)

### State Classes (Freezed - 12 files)
**Status:** Active, used with Riverpod
**Code Generation:** Yes (@freezed + build_runner)

**Pattern:**
```dart
@freezed
class FeatureState with _$FeatureState {
  const factory FeatureState({
    required DataType data,
    @Default(false) bool isLoading,
    String? error,
  }) = _FeatureState;
}
```

**Benefits:**
- Immutability
- copyWith() for updates
- Equality comparison
- Union types for complex state

**Files:** lib/data/state/ (separate files)

### Recommendation
**New features should use:** Riverpod with @riverpod + Freezed for state classes
**Rationale:**
- Consistent with 23 existing providers
- Code generation reduces boilerplate
- Better type safety
- Active migration from ChangeNotifier to Riverpod
```

---

## Presenting Discovery Findings

After all discovery tasks complete, present comprehensive findings to user:

**Template:**
```markdown
## Discovery Results

I've analyzed the codebase to understand existing patterns. Here's what I found:

### Similar Features
Found {N} existing features similar to {feature-name}:

1. **{Feature 1}** at {path}
   - Pattern: {description}
   - Components: {list}
   - Can be reused for: {purposes}

2. **{Feature 2}** at {path}
   - Pattern: {description}
   - Components: {list}
   - Can be reused for: {purposes}

[Full details in research.md]

### Project Structure
Your project organizes code as follows:

**Providers:** lib/data/providers/ (shared, {N} files)
**State Classes:** lib/data/state/ ({N} files)
**Feature Folders:** lib/ui/{feature}/ (screens/, widgets/, providers/)

**Naming Convention:** {pattern}

### State Management
Currently using: **{Primary approach}** ({N} files)
- Code generation: {Yes/No}
- Pattern: {brief description}
- Examples found: {paths}

Also found: **{Secondary approach}** ({M} files) - {status}

### Reusable Components Discovered
Found {N} components that might be useful:

1. **{Component 1}** at {path}
   - Purpose: {description}
   - Can be used for: {feature purposes}

2. **{Component 2}** at {path}
   - Purpose: {description}
   - Can be used for: {feature purposes}

---

## Next Steps

Based on these discoveries, I need to confirm a few architecture decisions with you before creating the implementation plan.

[Proceed to architecture confirmation questions]
```

---

## Tips for Effective Discovery

### Make Prompts Specific
```
// Bad - Too vague
"Find state management patterns"

// Good - Specific
"Find files using @riverpod annotation, count them,
show 2 complete examples with code"
```

### Request File Paths
Always ask for specific file paths, not just descriptions:
```
// Good
"Provide file paths for all provider files found"

// Result: lib/data/providers/org_providers.dart (23 files)
```

### Ask for Code Examples
Request actual code, not summaries:
```
// Good
"Show 2-3 complete examples of provider implementations
with file paths and full code"
```

### Parallel Discovery
Run all 3 discovery tasks in parallel to save time:
```
Launch 3 Explore agents simultaneously:
- Task 1: Similar Features
- Task 2: Project Structure
- Task 3: State Management

Wait for all to complete, then aggregate results.
```

### Handle "Not Found"
When discovery finds nothing:
```
Provider search found: 0 files

Interpretation:
- Project might not use providers
- Different state management approach
- Need to search for alternatives (Bloc, GetX, setState, etc.)

Action:
- Ask user what state management they use
- Or: Search for alternative patterns
```

---

## Common Discovery Patterns

### Pattern 1: Mixed Approaches
```
Found:
- 20 Riverpod providers
- 5 ChangeNotifier providers
- 3 files using setState only

Interpretation:
- Project migrating from Provider to Riverpod
- Some legacy code remains
- New features should use Riverpod (majority pattern)
```

### Pattern 2: Feature Folders
```
Found:
lib/ui/athletes/ (screens/, widgets/, providers/)
lib/ui/workouts/ (screens/, widgets/, providers/)
lib/ui/groups/ (screens/, widgets/)

Interpretation:
- Feature-folder structure
- Some features have dedicated providers
- Others use shared providers
- New feature should follow same structure
```

### Pattern 3: Shared vs Feature-Specific
```
Providers found:
- lib/data/providers/ - 15 shared providers
- lib/ui/*/providers/ - 8 feature-specific providers

Interpretation:
- Shared providers for app-wide state (auth, org, hardware)
- Feature-specific providers for page state (forms, filters)
- New feature needs both (shared for data, specific for UI state)
```

---

## Validation Checklist

Before presenting findings to user:

- [ ] Found at least 1 similar feature (or explained why none exist)
- [ ] Identified where providers are located (shared vs feature-specific)
- [ ] Identified state management approach (Riverpod, Provider, Bloc, etc.)
- [ ] Found reusable components or explained none found
- [ ] Provided file paths for all discoveries
- [ ] Included code examples (not just descriptions)
- [ ] Explained patterns clearly
- [ ] Ready to ask architecture confirmation questions based on findings

---

## Related References

- [agent-prompts.md](agent-prompts.md) - Reusable agent prompt templates
- [examples.md](examples.md) - Complete discovery workflow examples
- [patterns.md](patterns.md) - Common architectural patterns found
