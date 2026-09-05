# Household Chore Manager — Project Specification & Homework Scope

## 1. Overview & Vision
The **Household Chore Manager** is a lightweight, full-stack web application designed for a shared student or roommate apartment. It automates chore distribution through a **fair rotation mechanism based on weighted effort points**, tracks recurring tasks on a strict weekly cycle, uses the **honor system** for task completion, and enforces accountability through a **negative penalty system** for overdue tasks.

The system intentionally avoids heavy authentication and complex JavaScript dependencies, relying on Django's server-rendered templates and modern classless CSS.

---

## 2. Core Functional Requirements

### 2.1 Rotation Dynamics & Fair Allocation
* **Weighted Effort Notation:** Every recurring chore has an assigned point weight (e.g., Quick Trash Run = 1 pt, Bathroom Deep Clean = 4 pts).
* **Lowest-Score Priority Assignment:** When a cycle's assignments are calculated, tasks are distributed to the roommate currently possessing the lowest cumulative score. Ties are broken deterministically (e.g., least recently assigned or primary key order).
* **Strict Recurring Cycles:** Chores operate on fixed calendar days (e.g., Monday trash, Wednesday dishes, Sunday deep vacuuming).

### 2.2 Completion & Accountability
* **Honor System Completion:** Any household member can mark a chore assignment as completed with a single action. Upon completion, the task's point value is immediately credited to the assigned roommate.
* **Negative Overdue Penalties:** If a chore's due date passes and it remains pending, the task is marked `PENALIZED`. The assigned roommate is penalized by deducting the chore's point weight (or applying a configured deficit penalty), depressing their score and ensuring they are prioritized for subsequent chores.

### 2.3 User Experience & Access Model
* **Single Shared Household (No Auth):** No user logins, passwords, or multi-tenant accounts. The dashboard is publicly accessible to anyone on the local network. 
* **Dropdown Actor Selection:** Actions (marking complete) are executed by selecting the appropriate roommate from a dropdown or directly clicking the action button corresponding to the assigned roommate.
* **Admin Management:** Chores and roommates can be seeded and managed using Django's built-in Admin portal (`/admin/`).

---

## 3. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | Python 3 + Django 5.x | Batteries-included web framework with robust ORM, forms, and admin interface. |
| **Database** | SQLite 3 | Zero-configuration file-based database ideal for small, single-node deployments and homework grading. |
| **Frontend** | Django Templates | Server-side HTML rendering without client-side state synchronization overhead. |
| **Styling** | Pico.css | Classless semantic CSS framework for clean, modern, responsive styling without writing custom CSS or bundling assets. |
| **JavaScript** | None | 100% pure standard HTML form POSTs and redirects. |

---

## 4. Data Models Architecture (`models.py`)

### 4.1 `Roommate`
Represents a resident in the shared household.
* `name` (CharField, max_length=60): Roommate's display name.
* `total_points` (IntegerField, default=0): Cumulative running score reflecting completed tasks minus penalties.
* `created_at` (DateTimeField, auto_now_add=True): Timestamp of creation.

### 4.2 `Chore`
Represents a recurring household chore template.
* `title` (CharField, max_length=100): Name of the chore (e.g., "Empty Kitchen Trash").
* `description` (TextField, blank=True): Details or instructions.
* `weight` (PositiveIntegerField, default=1): Effort value (e.g., 1–5 scale).
* `recurrence_day` (IntegerField, choices=DAYS_OF_WEEK): Designated day of the week (0 = Monday, 6 = Sunday).
* `is_active` (BooleanField, default=True): Allows pausing chores without deleting history.

### 4.3 `ChoreAssignment`
Represents a specific scheduled occurrence of a chore.
* `chore` (ForeignKey -> `Chore`, on_delete=CASCADE): The parent chore template.
* `assigned_to` (ForeignKey -> `Roommate`, on_delete=CASCADE): The assigned resident.
* `due_date` (DateField): The target completion date.
* `status` (CharField, choices=[`PENDING`, `COMPLETED`, `PENALIZED`], default=`PENDING`).
* `completed_at` (DateTimeField, null=True, blank=True): When marked complete.

---

## 5. Algorithmic Logic & Business Rules

### 5.1 Weekly Schedule Generator
```python
def generate_weekly_assignments(target_week_start):
    """
    Generates assignments for Monday through Sunday of target_week_start.
    Chores are ordered descending by weight so the highest-effort tasks
    are distributed first to the roommates with the lowest current points.
    """
    active_chores = Chore.objects.filter(is_active=True).order_by('-weight')
    
    for chore in active_chores:
        due_date = target_week_start + timedelta(days=chore.recurrence_day)
        
        # Avoid duplicate assignment for the same week cycle
        if ChoreAssignment.objects.filter(chore=chore, due_date=due_date).exists():
            continue
            
        # Select the roommate with the lowest current total points
        candidate = Roommate.objects.order_by('total_points', 'id').first()
        
        if candidate:
            ChoreAssignment.objects.create(
                chore=chore,
                assigned_to=candidate,
                due_date=due_date,
                status='PENDING'
            )
            # Temporarily increment or simulate points to balance intra-week batching
            candidate.total_points += chore.weight
            candidate.save()
```

### 5.2 Completion Handler
When a roommate completes an assignment:
1. Validate that the assignment status is currently `PENDING`.
2. Transition `status` to `COMPLETED`.
3. Set `completed_at` to `timezone.now()`.
4. Ensure points are permanently locked to `assigned_to.total_points`.

### 5.3 Penalty Scanner
A lightweight management command or hook (e.g., `python manage.py run_penalty_check`):
1. Query all assignments where `due_date < timezone.now().date()` and `status == 'PENDING'`.
2. For each overdue record:
   * Set `status = 'PENALIZED'`.
   * Deduct `chore.weight` from `assigned_to.total_points`.
   * Save both records.

---

## 6. Views and URL Routing

1. **`GET /` (Dashboard View):**
   * **Leaderboard Widget:** Table displaying all roommates ranked by `total_points` descending.
   * **Active Chores Board:** Cards/table showing this week's assignments, grouped by day, showing chore title, weight badge, assigned roommate, and status.
   * **Action Trigger:** Inline HTML form (`POST /assignments/<id>/complete/`) to complete tasks.
2. **`POST /assignments/<id>/complete/` (Action View):**
   * Updates assignment and points, then redirects back to `/`.
3. **`GET /generate-cycle/` (Manual Trigger View / Admin):**
   * Quick utility button on the dashboard to trigger generation for the current or upcoming week.
4. **`/admin/` (Django Built-in Admin):**
   * Complete CRUD operations for adding/editing roommates, chores, and viewing historical logs.

---

## 7. Frontend Layout & Pico.css Styling

The application uses **Pico.css** via CDN (`https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css`), requiring semantic HTML without custom utility classes:
* `<main class="container">` wrapping the content.
* `<nav>` with brand name and links to Admin.
* `<article>` cards for the Leaderboard and Assignment table.
* Native HTML buttons (`<button class="outline">Complete</button>`).
* Badges and status pills using standard `<mark>` or small semantic spans.

---

## 8. Milestone Implementation Checklist

- [ ] **Step 1: Project Setup**
  - Run `django-admin startproject config .`
  - Create app: `python manage.py startapp chores`
  - Configure `settings.py` (add app, static files, templates).
- [ ] **Step 2: Define Data Models**
  - Implement `Roommate`, `Chore`, and `ChoreAssignment`.
  - Run `makemigrations` and `migrate`.
  - Register models in `chores/admin.py`.
- [ ] **Step 3: Assignment & Penalty Logic**
  - Implement rotation assignment service in `chores/services.py`.
  - Implement penalty evaluation logic.
- [ ] **Step 4: Views & Templates**
  - Build `base.html` with Pico.css CDN link.
  - Build `dashboard.html` with leaderboard and weekly chore table.
  - Implement `complete_chore` POST view with CSRF protection.
- [ ] **Step 5: Testing & Polishing**
  - Seed initial roommates and test chores.
  - Test edge cases (ties in points, completing past chores, penalty triggers).
