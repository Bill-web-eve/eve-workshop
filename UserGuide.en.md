# EVE Workshop – complete user guide

## Using the documentation

Open **Documentation** at the bottom of the left menu to read the complete guide inside the application. It is available without an EVE login or a selected production plan. The bundled guide also works offline while the local app is running. Its language follows the Magyar / English switch, and its appearance follows light or dark mode.

Use the **Table of contents** to jump to a chapter. **Search the user guide** searches chapter titles and their entire text. Multiple words must all occur in a chapter; accents are optional. **Clear search** restores all chapters. **Download user guide** saves the complete guide in the current language as a Markdown file. **Print / PDF** prints the whole guide, including chapters hidden by a search; choose Save as PDF in your browser's print dialog to create a PDF.

## Interface language

Use **Magyar / English** under **Settings → Appearance and language**. The change is immediate, and the application window remembers it. Your current inputs, filters and unapplied changes remain in place. Character, corporation, saved-plan and EVE item names are not translated.

EVE Workshop runs locally on macOS or Windows 11 64-bit. Excel and an OpenAI API subscription are not required. The browser interface connects to the app running on your own computer.

## Mac application window – test version

The new local Mac test version runs in its own application window, without an address bar or browser tab. It uses the existing local profile for characters, saved plans, inventory and settings. There is no Windows windowed test package yet; previous Windows releases retain their browser interface.

**Settings → Appearance and language** contains the dark-mode switch and Magyar / English buttons. **⌘,** opens this section; **⌘R** reloads the interface. Window preferences are stored separately from the previous browser, so select the theme and language once on first use. Window size and position are remembered.

The red window-close button or **⌘Q** also shuts down the local Workshop service. Unapplied edits or a running EVE refresh prompt before quitting. Saved data is retained. CSV, ICS and guide exports use the Mac save dialog. Item names and Multibuy lists are copied as plain text.

EVE authorization opens the official EVE sign-in page in your system browser. After successful authorization, Workshop receives the result and returns to the relevant settings section automatically. You can close the browser's sign-in tab afterwards. The Client ID and callback URL do not change.

## Starting and stopping the application

On a Mac, open the **EVE Műhely** desktop shortcut or the installed **EVE Muhely.app**. The local installation uses **~/Applications/EVE Muhely.app**. Its program files are inside the application, so starting it does not depend on a cloud drive being available. A separately published source installation may also have **EVE Muhely.command** and an application copy beside its workdir folder.

Previous browser releases open **http://127.0.0.1:8765**. Starting the launcher again opens the existing instance. Closing the browser tab does not stop the app. Use **Stop application** at the bottom of the sidebar; saved data is retained. The next launch opens the app again.

The packaged Mac and Windows distributions include their runtime. A source installation needs Python and its cryptography dependency; its launcher can create its own environment and download dependencies on first use. No separate server, Docker, Node.js or database installation is needed for normal use.

## Planning without an EVE login

1. Type the English in-game name in **Product**, then select an actual search result. The shortcuts below the field show your saved plans.
2. Enter **Target quantity** in units and select **Calculate plan**.
3. On **Blueprint**, select manual parameter mode to edit ME, TE, runs per job and the total BPC runs available, if known. Apply the settings.
4. On **Inventory**, enter stock and the expected output of jobs already running. Work-in-progress values are units, not runs.
5. **Production plan** shows only remaining work, ordered from basic reactions through advanced materials and components to the final product. It displays the deficit, required runs, output and job batches.
6. **Material shortfall** expands only the remaining work into the basic materials you still need. Materials for an already available component are not requested again.

Manual changes are saved when you use the corresponding **Apply** button. A blank manual inventory or work-in-progress field uses automatic EVE data; in manual stock mode it means zero. An explicit **0** is an override and remains after refreshes. **Reserved elsewhere** removes stock from the amount available to plans. Clear an override to return to automatic data.

Automatic EVE inventory uses only **packaged** items for both personal and corporation production. Assembled ships and modules are considered in use: they neither cover the target nor supply production inputs. Packaged materials inside ships or containers still count. BPO/BPC ownership is handled separately. Manual stock overrides remain an explicit exception. After **Calculate plan**, a status below the target fields confirms the result; when no production remains, it explains how packaged finished products or active jobs cover the target.

## Mining ledger

**Mining ledger** in the sidebar combines the personal mining history of all connected characters, independently of the production inventory owner. Corporation observer data is not added again to the same personal totals.

For first use, open **Settings → Data access** and choose **Authorize mining ledger** for each character. Enable **esi-industry.read_character_mining.v1** in the EVE Developer application, then authorize the character already connected to the app. Existing scopes are preserved. **Refresh mining ledgers** fetches all characters. The shared EVE data check also refreshes the ledgers once at least one character has authorized access. The operation indicator shows the current character and page.

- Choose 7, 30 or 90 days, all local history, or a custom period. Both boundary dates are included; ledger dates use UTC.
- Filter by character and ore. **By character** and **By ore** show units, m³, refined value and totals.
- **Daily totals** shows refined values and a period footer using the same Jita pricing as the headline total. Refining leftovers carry forward to the next day within the selected period, separately for each character and ore type. Daily material outputs sum to the period output; rounding individual ISK rows may differ by a few cents. **Ledger entries** shows the dates and systems. Tables support sorting and collapsible column filters; character columns use a dropdown. Detailed entries can be exported to CSV.
- Values use the estimated refined material output at Jita buy, sell or split prices. Raw ore market values are neither shown nor requested. Detailed ledger CSV exports contain quantities and volumes. These are estimates at current prices, not historical sales proceeds.
- Refining uses the moon settings: nullsec Tatara, T2 rig, maximum skills and the configured implant. Ore is pooled by character and type within the selected period. Only complete portions are refined and material outputs are rounded down. Leftover ore and gas are not counted as refined products. Refining and market fees are excluded.

ESI currently provides 30 days of mining history, cached for up to 10 minutes. Downloaded history is kept locally. Refreshes replace each character/date/system/ore quantity rather than adding it again. History that expired from ESI before it was downloaded cannot be recovered. Removing a character also removes its local mining history.

Missing permissions, failed refreshes, unknown volumes and missing prices are shown explicitly; partial totals do not represent every character's complete mining activity. **Source and coverage** shows the last successful fetch and cache expiry. Mining history is not inventory: the ore may already have been sold or consumed.

## Corporation inventory and production

Open **Corporations** and use **Discover and refresh corporation data** to identify the corporations of your added characters. Inventory, blueprints and industry jobs are downloaded once per corporation. Adding several members does not multiply corporation stock. Personal character and location filters do not restrict discovery.

To enable corporation access:

1. If using your own EVE Developer application, enable **esi-assets.read_corporation_assets.v1**, **esi-corporations.read_blueprints.v1** and **esi-industry.read_corporation_jobs.v1**.
2. In **Corporations** or **Settings → Data access**, authorize corporation access for an appropriate character and select that same character during EVE login. Existing personal, skill and PI permissions are retained.
3. Asset and blueprint access requires the appropriate **Director** role; corporation jobs require **Factory Manager**. One authorized character per corporation is sufficient. Missing corporation access does not prevent personal planning.

Choose **Personal production** or **Corporation production · [name]** in **Production scope** above the product selector. A corporation plan uses only that corporation's stock, job outputs and blueprints. Personal inventory and other corporations are excluded. Manual stock, blueprint overrides and location selections are stored separately for each owner. Structure bonuses are shared settings.

A saved plan remembers its scope. Existing personal plans remain personal; create a new plan to use a different inventory owner. Reservations affect only other plans using the same owner. The combined shortfall calculates each owner's stock separately, then adds the purchase quantities together.

**Refresh EVE data** in corporation mode refreshes corporation data. In personal mode, previously enabled corporation data is also refreshed. A failed corporation lookup never silently substitutes personal inventory. Previous snapshots are retained, and a dependent calculation can pause until valid data is available. Delivered-job versus older-asset handling applies to corporation stock too.

## Sorting and filtering tables

Click a table heading to sort ascending, click again for descending, and a third time to restore the original order. Quantities sort numerically and dates chronologically. The original production-plan order follows production dependencies.

Column filters are closed initially. Use **Open filters** and **Close filters** above the table. Closing the row keeps active filters; the button shows how many are set. Character columns use a dropdown. The Moon column in **Production by moon** and **Ore volume and processing** also uses a dropdown containing the listed moons. Other columns accept free text. Column filters and any search field above the table work together. Numbers can be searched without thousands separators.

**Reset sorting and column filters** clears table settings. The visible/total row count indicates filtered rows. Table settings survive view changes and data refreshes during the current browser session; a page reload resets them. Sorting and filtering change presentation only, not calculations or reservations. Reference tables in this guide are reading material.

## Dark mode

Use **Dark mode** under **Settings → Appearance and language** to switch appearance. Dark mode is the default. The application window remembers the selection across reloads and app restarts. The theme applies to forms, tables, graphs and documentation.

## Copying an item name

Click an item name to copy its exact English name as plain text. Clicking **Ferrofluid**, for example, copies only `Ferrofluid`: no ID, quantity or formatting. A toast confirms the copy. Paste with ⌘V on Mac or Ctrl+V on Windows.

This works in production, shortfall, inventory, blueprints, jobs, reservations, production graphs and relevant skill/PI lists. Keyboard users can focus the name and press Enter. Actions that select graph nodes or open item details continue to work. The **Saved plans** shortcut row opens the plan without copying its name.

## Connecting to EVE: initial setup

An EVE Client ID and authorization for each character are required for automatic data. A packaged distribution may already include the public Client ID; in that case add your characters directly. Until authorization is complete, manual inventory planning remains available.

For your own Developer application:

1. Open the [EVE Developer application page](https://developers.eveonline.com/applications), sign in and create or edit an application.
2. Use a suitable name such as **EVE Muhely**, and choose a local/native/PKCE application if the portal asks for a type. Complete the required description fields.
3. Set the callback URL exactly to **http://127.0.0.1:8765/callback**.
4. Enable the personal read permissions listed below. PI uses CCP's manage-named scope, but Workshop only reads PI data.
   - **esi-assets.read_assets.v1**
   - **esi-characters.read_blueprints.v1**
   - **esi-industry.read_character_jobs.v1**
   - **esi-skills.read_skills.v1**
   - **esi-skills.read_skillqueue.v1**
   - **esi-planets.manage_planets.v1**
5. Save the application and copy its public **Client ID** into **Settings → EVE connection**. Workshop does not use a Client Secret; do not enter one.
6. Choose **Sign in with EVE Online** to add characters individually. Enter your password only on CCP's official login page.
7. Run **Refresh EVE data** to download personal assets, blueprints and industry jobs, plus authorized skills, queues and PI colonies. Corporation assets require separate corporation access.
8. The first successful refresh enables personal EVE inventory unless you explicitly chose a stock mode earlier. You can change this in **Settings → Structures and bonuses**. A deliberately selected manual mode is preserved by later refreshes. Select included personal characters under EVE connection.

macOS may request Keychain access when encrypted authorization is saved. You can revoke permissions through your EVE account. Adding a new feature's permission requires enabling the scope in the Developer application and authorizing the relevant character again; you do not have to delete all your existing characters.

## Skills and training

**Skills and training** shows every added character, independently of production character and location filters. Click a character or **Details** for the full **Training queue** and searchable **All skills**, including trained/active levels and skill points. Current training, subsequent entries, completion times and queue length are shown separately.

- **Red:** the character is not training, or the queue is empty or paused, when it has an available training place.
- **Amber:** continuous training will stop within five days. A gap inside the queue counts even if its last entry ends much later.
- **Green:** training is active and the loaded queue continues for more than five days.
- **Grey:** permission or data is missing, refresh failed, or the last verification is older than five minutes. Unknown data is not treated as proof of idle training.

Enable **esi-skills.read_skills.v1** and **esi-skills.read_skillqueue.v1** in your Developer application, then authorize skills for each character under **Settings → Data access**. Keep the same Client ID and callback. Selecting a different character during a permission expansion does not overwrite the existing character's authorization.

**Refresh skills** refreshes just skills; **Refresh EVE data** also checks them after industry data. A failed skill request does not invalidate industry inventory. An open, foreground skill view checks authorized data every minute while respecting EVE cache expiry. There is no monitoring or external notification while the app is stopped.

EVE can retain already completed queue entries until the character logs into the game. Known completed levels are included in trained levels and known SP. Active levels are displayed separately from EVE skill data because subscription restrictions or Expert Systems can make them differ. Enable **Show completed entries** to inspect retained completions.

## Accounts, Omega and MCT

Under **Settings → Accounts and training**, create a local account label, enter Omega status and expiry, and set the expiry of up to two MCT places. ESI does not provide an account identifier or Omega/MCT subscription expiry. These are manual records; the app does not request your account login, password or billing access. See [CCP's account-status notice](https://developers.eveonline.com/blog/caution-accountstatus-xml-aspx-deprecated-and-unreliable).

Group up to three added characters per account. A training place can be automatic, the base place, MCT 1, MCT 2 or manually excluded. A character blocked by an expired assigned MCT place, by another character occupying the available place, or by manual exclusion does not receive an idle-training warning. Unknown eligibility is not automatically considered blocked. Alpha status alone does not mean training is impossible; loaded SP and the five-million-SP restriction are also considered.

The skill view lists subscription expiries, flagging expired entries and those due within five days. The assigned training-place expiry limits the continuity estimate. An EVE refresh does not extend manually entered subscriptions: update them after renewal. These training-place assignments do not consume or disable industry slots. [CCP MCT information](https://support.eveonline.com/hc/en-us/articles/203411052-Multiple-Character-Training).

## Refreshing data and work in progress

**Refresh EVE data** downloads data that EVE currently permits to be refreshed, then recalculates the plan. Repeated clicks may return the same cached snapshot. Asset, blueprint and job snapshot times are visible per character under EVE connection. Stale data is labelled; unsuccessful character refreshes retain previous data and can prevent new EVE-mode calculations until resolved.

**In progress** warns when completed jobs are ready for collection, with a count in the sidebar. Collect them inside EVE and refresh the app afterwards.

Work-in-progress inventory equals **runs × output per run** for manufacturing and reaction jobs with **active**, **paused** or **ready** status. Research, copying, invention, delivered, cancelled and reverted jobs do not add output. Ready but uncollected output is still counted.

After collection, the asset and job caches can disagree temporarily. The app can wait for a newer asset snapshot instead of asking you to manufacture the output again or counting it twice. You can use a verified manual inventory override while waiting. Existing overrides survive EVE refreshes; clear a field to use automatic data again.

For location filtering, enter station or structure IDs under **Structures and bonuses**. Empty selection includes every location. Container contents are assigned to the enclosing top-level location; jobs use their output location.

## Blueprints and structure bonuses

Automatic blueprint mode reads ME, TE and remaining BPC runs from owned blueprints, even when material inventory is in manual mode. Personal or corporation blueprints follow the selected production scope. Stock mode controls material and work-in-progress deductions, not whether owned blueprint parameters are shown.

Separate columns show owned BPO/BPC counts, total copy runs and the usable runs of the selected ME/TE group. **View instances** lists each blueprint's ME, TE, remaining runs, location, character, unique Item ID and selection status. EVE instances remain visible while manual overrides are used.

BPOs take priority; within BPOs, or when selecting copies, the best ME followed by TE is preferred. Only BPCs with identical ME/TE are pooled. A new job starts at each copy's run boundary, with separate material rounding. Different parameter groups or occupied instances receive warnings. Choose an Item ID to select a specific blueprint. Two Salvation copies with ME 3, TE 2 and two runs each appear as **2 BPCs and 4 usable runs**.

Without a blueprint, a labelled manual calculation initially uses ME 0 and TE 0. Insufficient BPC runs do not suppress the material requirement for the full target; the missing runs are reported separately. This does not claim that all jobs can start immediately.

**Run/job** is an editable batching assumption. An automatic BPC default is at most 100 and the largest selected copy's remaining runs. BPO or missing-blueprint defaults are at most 100 and the catalogue copy-run limit. A saved manual Run/job value takes priority. Set it to the job size you intend to use because rounding depends on batches. Reactions always use ME 0 and TE 0.

Edit activity-wide bonuses under **Settings → Structures and bonuses**. Initial values are:

| Activity | Structure material | Rig material | Structure time | Rig time |
|---|---:|---:|---:|---:|
| Manufacturing | 1% | 4.2% | 30% | 42% |
| Reaction | 0% | 2.6% | 25% | 26.4% |

Bonuses multiply and apply to every step of the corresponding activity. The manual skill time factor defaults to 1.00 and is used only for manual time estimates. A selected character with valid skill data uses actual active skills instead; the manual factor is not applied again.

## Buying intermediates and updating recipes

Set an intermediate product to **Buy** on the Blueprint page to stop expanding its recipe. Its own inputs disappear, and the intermediate itself becomes a purchase requirement. Set it back to manufacturing to expand it again.

Fuel Block inputs are purchased by default. You can select Fuel Blocks as a target product or change an intermediate to manufacturing. PI products are purchase leaves in production planning; the separate PI view monitors colonies. Invention and copying are not expanded into their own research jobs.

**Save plan and reserve** stores the target and activates a stock reservation. Inventory and blueprint settings are shared within their scope. Production and shopping lists can be exported as CSV, and shopping lists can also be copied to the clipboard.

**Update recipe data** under Structures and bonuses downloads CCP's official SDE. The bundled catalogue can be used offline before an update. It contains published producible products, recipes, blueprint types, skill requirements, moon ores and relevant game data. Updating recipes does not replace character data or authorize new ESI access. See [CCP Static Data](https://developers.eveonline.com/docs/services/static-data/).

## Saved plans and finished products

The target is a desired total quantity, so existing finished products and active outputs reduce the amount left to make. If you own three Redeemers and want **three additional ships**, enter three in that product's **Reserved elsewhere (manual)** field on Inventory. Existing ships are then kept aside for every plan, while newly produced ships can still reduce the remaining target. Do not replace actual stock with a manual zero, which would also hide new ships after refreshes.

The production view separately shows how much of the target is covered by finished stock and active job output. An empty queue can therefore be correct even when the target quantity is large.

## Using reservations

1. Calculate the target, then use **Save plan and reserve**. The plan reserves available stock, allocated active-job output and usable BPC runs.
2. Selecting another product starts a new target. Other saved plans' reservations are deducted, so resources already allocated elsewhere appear missing. Use **New plan with this target** for a separate plan of the same product.
3. Open an existing plan from **Saved plans → Open plan** or its shortcut. It can use its own reservation. The status banner identifies a saved plan versus a new target, and a reload preserves that selection.
4. Editing quantity or producer previews a change. **Update plan and reservation** updates the same saved record. Earlier active reservations have priority; increasing one can reduce resources available to later plans.
5. **Reserved items** shows stock and active-job output separately. Inventory lists **Other plans' reservations** and **Own plan reservation**. BPC holds also show instance Item IDs and reserved runs.
6. **Release reservation** makes resources available elsewhere while keeping the plan. Deleting a plan also releases its hold. Reactivating a hold puts it after currently active reservations.

Reservations are recalculated from the current stock source, character/location filters, blueprint parameters and job sizes. Only available quantities are reserved; missing quantities remain manufacturing or purchasing requirements. When a component becomes available, the plan reserves that component and releases the raw materials previously needed to make it. Finished target products remain protected until you release the completed plan.

Reservations exist only inside Workshop; they do not move EVE items. BPC runs are held per physical copy, but BPOs and character industry slots are not reserved. Manual **Reserved elsewhere** is an additional deduction. A failed EVE refresh does not turn unknown stock into empty stock: refresh valid data or deliberately choose manual mode.

## Saved-plan categories and combined purchasing

**Saved plans** has separate Personal and corporation categories, aligned with **Production scope**. Only plans saved to the selected category are displayed. Saving uses that scope; updating an existing plan preserves its owner. Create a new plan to use a different owner. Personal and corporation reservations never mix.

The **Saved plans** shortcuts below the product field show only plans in the current scope, with their name and quantity. Clicking opens that same saved plan with access to its own hold and highlights it. Saving or deleting a plan updates the row. Selecting a plan keeps the current page open: the scheduler, graph, material shortfall and other views update for the selected plan without returning to Production plan. Scheduler options are retained; recalculate the schedule for the new plan. Unapplied edits require confirmation before switching. These shortcuts do not copy item names.

**Material shortfall → All saved plans** combines requirements into one row per material, with the total purchase quantity and a per-plan breakdown. Shared stock and active output are used once. Active reservations receive their existing priority; unreserved saved plans follow in creation order. Unreserved plans are included without activating their reservations. **Included plans** lists the goals and allocation order.

**Refresh summary** recalculates from local snapshots. Run **Refresh EVE data** first for new assets or jobs. The combined list can be copied and exported as CSV. **Selected plan** returns to the individual shortfall. Combined purchasing uses saved quantities, not unsaved product-field edits. Available components are not expanded back into their materials.

## EVE Multibuy lists and missing blueprints

Copying a selected or combined shortfall produces EVE Multibuy text: **English item name, tab, ungrouped integer quantity**, one item per line. There is no heading or unit suffix. Duplicate materials are combined. BPOs, BPCs, missing BPC runs and reaction formulas are excluded from the clipboard list and remain separately visible in the app.

Missing BPC capacity is shown in runs. With five required runs and a two-run copy, **three runs** are missing. The estimated number of copies depends on the displayed run/BPC assumption. Originals have unlimited run capacity. Copying, invention or purchasing can provide copies, but their separate jobs, inputs and lead times are not planned here. A missing reaction formula requires a purchase rather than a copy. The combined summary counts a reusable formula once per inventory owner.

Stock, ready components and active outputs are deducted before blueprint requirements. A component already covered does not require another BPC. Actual copy runs can be reserved by a saved plan, released or consumed only once. Personal and corporation copies remain separate. The missing-run unit must not be interpreted as raw-material units; procurement CSV columns distinguish units and runs.

## Production dependency graph

Open **Production graph** for the current target or saved plan. Arrows run from inputs to products. By default only remaining manufacturing and reactions appear, with the same quantities and runs as the table. Nodes show rounded output, deficit, free stock and active output after reservations.

- **Purchased materials** adds genuine purchase requirements. **Covered items** adds available components without rebuilding unnecessary raw-material branches.
- Each product has one node even if several downstream steps use it. Hover an arrow for that consumer's input quantity.
- Select a node to highlight its chain and inspect batches, inputs and consumers below. Nodes support keyboard selection.
- Use **+ / −**, **100%**, **Fit graph**, scrolling and dragging the blank background to navigate. **Jump to an item** centres and zooms to it. **Table view** returns to production.
- **Large view** expands the graph. **Normal view** or Escape restores it. **Details** opens the selected item's information.

## Quantities and character-based production time

Reaction targets allow up to **100,000,000 units**; manufacturing targets allow up to **1,000,000**. Quantity, inventory and run fields group digits in threes. Input with or without spaces is accepted.

Select one **Manufacturing character** per plan. This selection is saved and supplies the active skills for every manufacturing and reaction time estimate in that ordinary plan. Personal plans can select added characters; corporation plans use added members of that corporation. Selecting a producer changes the time estimate, not inventory ownership. The ordinary plan does not allocate multi-character slots; use Production scheduler for that.

Manufacturing applies Industry, Advanced Industry and catalogue-listed specialist time bonuses as separate factors. Reactions apply the Reactions skill time bonus. Blueprint TE and activity structure time bonuses also multiply. This time calculation does not include implants. **Producer / skill time** identifies the character and exposes skill bonuses and missing requirements; work-hour columns show each step's duration.

Without a selected character or valid skills, the estimate is labelled manual. A selected character missing requirements is flagged as unable to start the job. The **Manual skill time factor** applies only to manual estimates and is not multiplied into an ESI-derived skill factor. Future queue levels are not treated as active. Total work hours sum job durations; they are not the elapsed time of a parallel production schedule.

## Production scheduler

**Production scheduler** builds manually executable job assignments for the current product, quantity and personal/corporation scope. Select included characters, set options, and use **Calculate schedule**.

Manufacturing capacity is **1 + active Mass Production + active Advanced Mass Production**. Reaction capacity is separate: **1 + active Mass Reactions + active Advanced Mass Reactions**. Reactions and manufacturing can run concurrently on the same character. Research does not occupy manufacturing slots but can occupy a blueprint. Personal and loaded corporation jobs are deduplicated by Job ID. Missing job data, job snapshots older than a day, or stale/failed skills must be refreshed.

Only characters with verified active recipe requirements receive jobs. Durations use their skills, the selected TE and structure bonuses. Exclusion from training warnings does not exclude a character's industry slots. A manually entered Omega expiry can prevent future job starts until the subscription date or active skills are refreshed.

With **Use only owned BPOs/BPCs**, actual owned instances matching the selected ME/TE are required. Manual run budgets do not create physical blueprints. Runs held by other plans and already committed to active jobs are deducted. One blueprint cannot serve two simultaneous jobs, and copies with different ME/TE are not mixed.

With the owned-only restriction disabled, the scheduler may propose extra copies or formulas for parallel work. A separate table lists additional instances, runs and assumed run/BPC sizes. Their availability is the supplied material/new-blueprint arrival time; copying or invention lead time is not independently simulated.

Personal blueprints are used by their owner unless **Personal blueprints can be transferred between characters** is enabled. Such jobs are marked for transfer. Corporation schedules use only that corporation's stock, blueprints and added member characters. Physical location, hauling and corporation launch/hangar permissions are not verified.

Stock is available at the start. Work-in-progress becomes usable at the associated job's end. Manual work-in-progress without a verified arrival can leave the schedule partial. Purchased materials and new blueprints arrive at the specified time; leaving it empty assumes they are ready at the start. Dates entered in the form use local time.

Inputs are spent only once, and a job waits for every required quantity before starting. Several batching strategies are compared for a shorter complete schedule. This is a heuristic estimate, not a guaranteed mathematical optimum. It assumes immediate job collection and item transfers. Workshop never launches an EVE job or changes actual inventory.

Batch changes can alter rounding, so the scheduler recalculates and displays its own material shortfall, with Multibuy copy. It does not update the saved plan's reservation. Export the schedule as CSV if needed. At most 10,000 jobs can be planned; tables and the timeline show 100 jobs per page.

### Schedule graph and timeline

Separate **Reaction schedule** and **Manufacturing schedule** tables use independent slot budgets. The common timeline shows separate lanes per character, activity and slot. Use the character selector to display everyone or a single character. Filtering changes only the timeline, not the schedule or tables; the time axis stays the same across characters within the selected period. Selecting another character's job adjusts the filter and page.

Select a timeline bar or a Job number to inspect each input's quantity, source and arrival, plus downstream consumers. Job links can jump across pages. Timeline and activity tables paginate separately. Stock, purchases, existing active output and new scheduled output remain distinct sources. A job can still wait for a slot or blueprint after its materials arrive.

Consecutive reactions on the same character, slot and physical formula are combined only when all inputs were available at the first start and no consumer would be delayed. The combined material rounding and dependency references are rebuilt. Short jobs needed for early downstream output or later input arrivals remain separate.

### Jobs already running in EVE

The timeline also shows loaded **active** manufacturing and reaction jobs that are still running, produce an item in the selected plan and belong to the selected characters, inventory owner and location filter. A green dashed border, **EVE** label and **Running in EVE** marker distinguish them from proposed work. They have separate EVE lanes and are not added again to planned runs, purchasing or the new-job CSV.

Select a running bar for its original EVE Job ID, character, start/end, runs/output, progress estimated from timestamps and job snapshot time. Older snapshots receive a grey marker. When the expected end passes, the label changes to **Expected complete**; refresh EVE data and recalculate to confirm the actual state. A planned job never becomes an actual running job just because its proposed start time has arrived. Paused, ready and delivered jobs are not shown as running.

On wide screens the plan selector and scheduling settings appear as two compact side-by-side cards; smaller screens stack them. Expand **Scheduling notes** for explanations of minimum job duration and material arrival.

### Visible days on the timeline

Set **Visible days** in **Schedule graph and timeline** to any whole number from **1 to 3650**. The default is up to **7 days** at once, and your browser remembers the setting. Leave the field empty or choose **Full time range** to fit the entire schedule.

Use **Previous period / Next period** to move between windows containing the selected number of 24-hour days. The last period can be shorter when the schedule ends earlier. The displayed dates and period counter identify the current window. A job crossing a boundary appears in each overlapping period, with only its visible portion drawn. Its tooltip and details retain the full job times.

The character filter applies within the same time window. The separate 100-job pagination pages through jobs matching that period and character; it does not change periods. Selecting a job in another period automatically moves the timeline to it. A new calculation starts at the first period. This setting does not change job durations, minimum job duration, material dependencies, activity tables or the CSV export.

### Minimum job duration

**Minimum job duration (hours)** defaults to **12** and is remembered in your browser. It applies to manufacturing and reactions using actual skill-, TE- and structure-adjusted duration. It may increase ordinary Run/job batches and balance job sizes to avoid tiny remainders. Set it to **0** to disable the minimum and retain ordinary Run/job limits.

No mandatory waiting time is inserted between jobs. A successor can start as soon as its inputs, slot and blueprint are available. The scheduler never produces extra runs solely to fill the minimum. BPC boundaries, recipe run caps and maximum job duration still apply; unavoidable shorter jobs are marked in the tables.

## Jita prices and material cost

Select **Jita sell**, **Jita buy** or **Jita split** outside the cost tables. Split is the mean of buy and sell. The choice is shared across pricing views and remembered by the browser.

Prices are based on public Jita 4-4 market orders, loaded in the background. Refresh respects EVE's market cache. Price timestamps and the number of unpriced items are shown. Missing prices are excluded from subtotals and flagged, rather than treated as confirmed zero prices. BPC runs are not valued using BPO market prices.

**Production material cost** includes the value of existing inputs used by remaining production. Shortfall cost includes only quantities still to buy. Shortfall rows show individual values and an overall total. In a combined saved-plan list the same inventory is not counted twice.

The target product's gross **Jita buy** and **Jita sell** sales values are displayed together for the full target quantity. **Sell price per unit · Jita sell** shows its unit sell price independently of input-price mode. Missing offers give an unknown value. Because finished stock reduces remaining work, the remaining production cost and full-target sales value can have different quantity bases.

## Job cost and production location

Under **Settings → Structures and bonuses**, choose a system from the filtered search results separately for manufacturing and reactions. System cost indices come from ESI. Enter **Facility tax** and adjust the structure job-cost reduction, SCC surcharge and any Alpha surcharge as appropriate.

After saving bonuses, the production cost summary shows job cost, total remaining production cost and a fee breakdown. The fee base uses adjusted prices; indices and adjusted prices are refreshed in the background with EVE caching. An unavailable index or price is labelled instead of silently providing a complete estimate. Check the activity and facility settings before comparing plans.

The displayed product sale values are gross estimates; do not interpret a material subtotal alone as net profit. Ordinary manufacturing labour, hauling and extra costs not represented by these fields are not automatically priced.

## Moon register and 30-day production

Expand **Moon management** in the sidebar. **Moon register** lets you add, edit or delete moons.

1. Start typing the system name and select a result. The constellation and basic system data are obtained from ESI and cached.
2. Select the moon and drilling structure, **Athanor** or **Metenox**. Choose up to four distinct ore types from dropdowns and enter their percentages. Fewer than four ores are allowed.
3. Check the percentage total. Totals above 100% are invalid and excluded from production. Below 100% is a partial composition: only declared ores are calculated, without distributing the undeclared remainder. Manual ratios are not silently corrected.
4. Set whether the drill is active, the number of online starts, estimated belt lifetime, monthly rent and other costs. Disabled drills contribute neither production nor continuous consumption. Saving updates the summaries.

**30-day production** projects **720 hours** of ore volume and processed materials. View individual moons or totals, filtered to all structures, Athanors or Metenoxes. The Moon columns in **Production by moon** and **Ore volume and processing** use dropdown filters. The combined-material table gives each row a value at the selected Jita price mode.

Athanor processing assumes a **nullsec Tatara, T2 moon-ore rig and maximum refining skills**. Configure the refining implant under **Settings → Moon calculation settings**; it defaults to **4%**. The mining recovery percentage is also adjustable. The displayed Tatara yield is the processing multiplier.

Metenox uses its own mining efficiency and per-cycle downward rounding. Only moon materials are added, not ordinary minerals contained in the ore. Ore recipes and machine parameters come from the bundled catalogue.

These are projections, not a measurement of material actually mined or hauled. Fresh identifiable ESI ore composition can replace the ratios used in Athanor calculations while preserving the original manual inputs. Sources are explicitly marked.

## Moon consumption

**Consumption** shows each drill's 30-day Fuel Block requirement, Metenox Magmatic Gas consumption and the one-off fuel for configured online starts. Quantities and ISK values are available per moon, per structure type and combined.

Choose one of the four Fuel Block types. **Manual Fuel Block unit price (ISK)** overrides its market price; leave it blank to restore Jita pricing. Apply the fuel settings to save them. The price field groups digits in threes while keeping decimals. Magmatic Gas uses the selected Jita buy/sell/split mode.

The separate Tatara and unrelated service modules are outside the drill fuel budget. Add their cost as other monthly costs if required.

## Moon production value and profit

**Production value at Jita** includes Fuel Blocks, Magmatic Gas, entered rent, other costs, sales fees, total costs and **Profit / 30 days**. Under each moon's Edit form, enter monthly rent and other expenses, such as refining, mining, hauling or separate Tatara fuel. These are not automatically inferred.

Set sales tax and broker fee under **Settings → Moon calculation settings**; both initially default to zero. Selling to buy orders does not incur a new sell-order broker fee. Sell and split valuations include the configured broker fee. The structure filter applies to costs and profit as well as output.

Missing market prices make the valuation incomplete and are reported. Manual Fuel Block pricing applies to the consumption and profit calculations, while the output material price mode remains selectable.

## Extraction calendar and ESI ore quantities

**Extraction calendar** shows extraction events identified for registered moons. **Extractions and expected ore** appears above the calendar. Open a row or event to inspect the moon, chunk arrival, automatic fracture, total and per-ore cubic metres, data source, freshness and estimated ore disappearance.

An enabled Athanor without an accessible extraction receives a warning. This means the app has no matching data; it does not prove that no extraction exists in EVE.

Enable the relevant characters under **Settings → Data access → Moon data access**, then refresh moon data. Required permissions are:

- **esi-calendar.read_calendar_events.v1**
- **esi-industry.read_corporation_mining.v1**
- **esi-characters.read_notifications.v1**

For your own Client ID, also enable these in the Developer application. Notifications require a character who actually receives the moon mining notifications in EVE. Corporation timers require the appropriate **Station Manager** role in the corporation owning the drill. A rented drill owned by a different corporation may remain invisible to corporation timers.

The character's **moon mining notifications** are the primary source of ore quantities. A fresh identifiable notification with per-ore volumes supplies the used ratios and is marked as an ESI notification. Unambiguous calendar text can also provide quantities. Corporation timers alone do not contain composition: their duration can provide an estimated volume using manual ratios. Missing, stale or unparseable composition does not replace the manual data.

Disappearance is an estimate based on observed or possible fracture times plus the moon's configured belt lifetime. An unknown fracture can produce a range or unknown expiry. It is not a guaranteed ESI expiry. App calendar tables label UTC; local calendar subscriptions use the calendar application's timezone.

## Mining crystals

Select a moon in **Mining crystals**. Usable extraction ore volumes take precedence; otherwise the app uses that moon's 30-day projection. Ores needing the same crystal are grouped before proportions are calculated. Choose the crystal variant under Moon calculation settings. Metenox does not need crystals.

Each suggested crystal count is a whole number from **1 to 9**. Exact simplified ratios are retained when all terms fit, so **75% : 25% becomes 3 : 1**. Otherwise the largest term is scaled to nine, terms are rounded upwards, and common factors are removed. A required type is never rounded to zero; **99.99% : 0.01% becomes 9 : 1**, and **37.3% : 62.7% becomes 2 : 3**.

The table shows crystal, ores, volume and share. These counts are a proportional stock suggestion, not the number consumed during the whole mining operation. Crystal wear, laser count and mining yield are not included. The crystal page does not show Tatara refining yield.

## Synchronizing with a local calendar

Under **Settings → Calendar sync**, enable the feed and choose **Subscribe in your local calendar**. On Mac, select **On My Mac** and hourly auto-refresh. You can also copy the subscription URL into a compatible calendar client. See [Apple calendar subscriptions](https://support.apple.com/en-ie/102301).

The feed includes loaded extraction events for enabled Athanors, with the moon name and chunk arrival. Descriptions include known ore quantities and estimated disappearance information. An event marks a time, not a mining duration. The calendar displays times in its own timezone.

The app must be running for calendar refreshes, and EVE data must still be refreshed to obtain new events. Reading the feed does not initiate an ESI refresh. The localhost feed works only on this computer; cloud calendar servers and other devices cannot access it.

The subscription is read-only. **Replace URL** invalidates old links, requiring a new subscription. Disabling synchronization removes feed access; already downloaded events must be removed in the calendar client if desired. Treat the subscription URL as a private local access link.

**Download ICS** gives a one-time import file, not an automatically updating subscription. Repeated imports can duplicate events in some calendar clients. Use a subscription for continuing updates.

## Shared settings

Expand **Settings** in the sidebar for:

- **Structures and bonuses:** manufacturing/reaction material and time bonuses, production systems, facility fees, stock source, location filters and recipe updates.
- **EVE connection:** Client ID, character authorization, personal character selection and removal.
**Authorize all access** requests every permission supported by the app for one character in a single EVE login: personal inventory, blueprints and jobs, skills and training queue, PI, corporation data, moon calendar and notifications, intel location and mining ledger. Select the same character on the EVE page. With your own Client ID, enable all requested scopes in the Developer application; corporation data still requires the appropriate in-game roles. Refresh EVE data after approval. Individual authorization buttons remain available.

- **Data access:** per-character skill, PI, corporation and moon permissions, scopes and refresh actions.
- **Moon calculation settings:** refining implant and recovery, crystal variant, fuel type, manual fuel price and economic parameters.
- **Calendar sync:** local subscription and ICS export.
- **Accounts and training:** local account groups, Omega/MCT dates and training-place assignments.
- **Notifications:** OS permission, alert types, background refresh, moon look-ahead and ownership.

Operational views link to the appropriate settings instead of repeating configuration panels. After authorization, the relevant Settings tab is reopened. Unapplied edits prompt before leaving their view.

## Request and operation progress

During a request or calculation, the top bar shows the number of active operations and a detailed status panel appears at the bottom right. It remains visible across navigation and scrolling. **Minimize** collapses it; the top-bar status button opens it again.

EVE checks show the current stage, character or corporation, checked count, resource type and page progress. Valid EVE cache use and waiting for an EVE response are labelled separately. Jita prices and industry cost data have independent progress rows. Plan calculations, searches, saves and other data requests are also tracked.

A progress bar follows a known item count; an indeterminate indicator is used when the full amount is unknown. **Elapsed time** is not an estimated completion time. Parallel operations are listed separately. A successful start response does not mean the background refresh has finished.

Completion is marked **Complete**, **Warning** or **Failed**. Failures affecting individual characters or resources produce a partial result. If status polling itself fails, the panel explains that it is retrying and does not claim completion. Labels follow the selected Hungarian or English language.

## Notifications and macOS alerts

The sidebar **Notifications** menu collects idle characters, queues ending within five days, completed jobs, stopped PI production and moon extractions due within the next **3 days**. Open an alert to visit its related view. The sidebar badge counts reliable current alerts; a question mark means data needs review.

The **Personal** tab contains personal jobs, character training and PI colonies. The **Corp** tab filters corporation jobs and assigned moons by corporation. A corporation job is not duplicated in the personal list. Training and PI remain personal character data. Missing, stale, failed or unauthorized data appears under **Data to review** and does not trigger an OS notification. Characters excluded by Alpha, MCT or manual training-place settings do not receive a false idle-training alert.

Jobs reported ready by EVE are distinguished from jobs expected to have finished based on their end time. Snapshot-based PI stop forecasts are marked as estimates. An alert does not deliver jobs, start production or change inventory.

Under **Settings → Notifications**, choose **Authorize system notifications**, then approve the macOS permission prompt. Use **Test notification** to check display. Configure personal/corporation and category switches, change the moon look-ahead from 1 to 30 days, and enable automatic EVE checks every four minutes. EVE cache expiry is respected. **Check EVE data** also starts a manual refresh.

Moon ownership is inferred from ESI corporation timers. Unknown ownership stays in Personal with a label. In **Moon notification ownership**, choose automatic, personal or a specific corporation. This changes alert classification only.

Each event is sent once per active episode; restarting the app or repeating a refresh does not resend it. Simultaneous alerts are grouped by owner and category. Clicking an OS notification opens its corresponding tab and category. macOS Focus and notification settings can affect presentation.

**Keep the application running**; monitoring also works in the background. A closed app performs no new EVE checks and sends no new OS notifications. OS delivery is available in the local macOS window preview; browser users can use the in-app notification list.

## Delivered jobs and delayed asset updates

If a job has been delivered but the asset snapshot predates delivery, Workshop can show **Waiting for inventory refresh**. It lists affected character, material, stock timestamp, delivery time and EVE cache expiry. Repeating refresh before expiry can return the same data.

**Calculate plan** shows a visible error in every view, including the scheduler, when inventory refresh is required. It names the affected plan and materials and gives the **earliest refresh attempt** with the full date, seconds and time zone in your browser’s local time. After that time, use **Refresh EVE data**; Calculate plan only recalculates from local snapshots. An already expired cache is explicitly labelled. The message and date follow the selected UI language.

Saved plans and holds are retained. In an open foreground app, a refresh is attempted after the indicated expiry, at most once per minute, without interrupting another refresh or unapplied manual edits. Expiry does not guarantee that EVE has a newer snapshot; another wait can be necessary. There is no background check after the app is stopped.

Delivered output is not simply added to old assets, which would double-count it when updated stock arrives. Items already fully covered by stock or active output do not cause this wait. A fresh snapshot resumes calculation with actual inventory. You do not need to delete or release the saved plan to recover.

## Windows 11 64-bit

Extract the Windows ZIP with **Extract All**, then run **EVE_Muhely.exe** inside the extracted **EVE Muhely** folder. Keep the whole folder together and do not run the executable inside the ZIP. Python, Excel and Codex are not needed. The UI opens at **http://127.0.0.1:8765**. **Inditas.cmd** is an alternative launcher.

Distributions contain no characters, saved plans, personal stock or authorization tokens. Only the public Client ID can be preconfigured; each user authorizes their own characters. Windows stores personal data under **%LOCALAPPDATA%\EVE Muhely**. Windows protects the token encryption key for that user account; on another machine or Windows user account, sign in to EVE again.

Stop the app before replacing its program folder. The separately stored profile is preserved. **Ellenorzes.cmd** runs checks with a temporary test profile, including encryption, the local API, saving plans and EVE HTTPS access; it does not add real characters or change plans. Unsigned packages may trigger the operating system's normal publisher prompt. Do not disable antivirus or SmartScreen.

## Files, backups and updates

Your Mac profile is stored at **~/Library/Application Support/EVE Muhely/**. Windows uses **%LOCALAPPDATA%\EVE Muhely**. These profiles are separate from program files and are not automatically saved to a source-code repository or cloud workdir.

**muhely.sqlite3** holds settings, snapshots, plans and other local records. Stop the application before making a manual backup. **characters.enc** contains encrypted authorization; the encryption key is protected by macOS Keychain or Windows user protection. Copying files alone to another machine does not restore logins: authorize characters again there.

For source installations, program files, the recipe database and tests may be under **workdir/eve_muhely**. Updating source alone does not replace an installed local app; update that application too. Packaged releases and local source launchers have different runtime arrangements, but use the same separate profile location.

Startup errors can be investigated in **server.log** and **launcher.log**. Access tokens are not deliberately logged. Exported CSV or clipboard lists represent one calculation at one moment; regenerate them after stock or plan changes. This guide is bundled with the app and changes when the application is updated.

Official background: [EVE SSO](https://developers.eveonline.com/docs/services/sso/), [ESI best practices](https://developers.eveonline.com/docs/services/esi/best-practices/), [CCP PI guide](https://developers.eveonline.com/docs/guides/pi/).

## Troubleshooting common situations

- **The production list is empty:** check how much finished stock and active output covers the target. Verify scope, other-plan reservations and manual overrides. Keep existing products aside using Reserved elsewhere if you want additional new units.
- **Materials for an already built component are still missing:** verify stock source, character/location filters, corporation versus personal scope, reservations and asset timestamp. Only actually available components can be deducted.
- **Refresh keeps returning old data:** EVE may return the same cache until expiry. For delivered jobs, wait for the displayed asset refresh or apply a verified manual stock override. Do not delete the reservation merely to clear the warning.
- **invalid_scope or missing access:** enable the scopes in the Developer application, then authorize that character again under Data access. Corporation endpoints also require in-game roles. Never enter a Client Secret or EVE password into Workshop.
- **The schedule is partial:** inspect blocked items and character capacity. Check active skills, fresh job snapshots, physical blueprints, Omega dates and material arrival. Partial output does not mean the whole target is covered.
- **A local update is not visible:** reload the page with ⌘R on Mac or Ctrl+R on Windows, then recalculate the plan or schedule. Use Stop application to shut down; closing the tab is not enough.

## Intel map and local chat log monitoring

Open **Intel map** in the sidebar; no production plan is required. The app checks the configured EVE Chatlogs directory every second and reads newly appended lines. The native Mac window can send system notifications in the background. Monitoring stops when the app closes. Enable chat logging in EVE and join the monitored channels. This is reported intel, not a complete or guaranteed live picture of the game.

1. Open **Settings → Intel settings**.
2. Select the **Chat log folder**, using the native **Choose folder** button on Mac or entering a path. **Discover channels** lists channel names from filenames; click to add them. Enter one exact name per line in **Monitored channels**.
3. Enable monitoring. Set the alert radius (0–30 stargate jumps), intel lifetime (1–120 minutes), and notification cooldown for the same system (0–600 seconds). Zero jumps means the same system only.
4. Select the characters to monitor. **Authorize intel location** adds `esi-location.read_location.v1` and `esi-location.read_online.v1` to the character's existing grants. Enable both scopes in the EVE Developer application for your Client ID. You approve the EVE login and grants yourself.
5. Alternatively, select a **Manual reference system** from the type-ahead search. This pins a reference; it does not follow movement. Clear it to resume automatic positioning.
6. Save. For OS alerts, enable **Personal alerts**, **Nearby intel** and system notifications in **Settings → Notifications** and grant macOS permission. Intel notifications have an optional sound.

Reliable ESI positioning requires both a fresh location and an online character. Failed, expired or offline ESI data cannot establish current proximity. Your character's Local system-change log supplies a last known location. **Also alert using a fresh Local log location** explicitly enables this less certain fallback; data must be no older than five minutes and does not prove online status. The location source and its time are shown.

## Intel message interpretation and clear

The parser recognizes full system names and unambiguous uppercase prefixes of at least three characters containing a digit or hyphen. An optional region narrows prefix matching. Reports mentioning several systems are marked ambiguous and do not trigger alerts. A clear arrow route uses its destination system.

- `J5A-IX Pilot Name` reports a pilot in a system. The reporter stays in a separate column and is never automatically counted as the reported pilot.
- A character showinfo link supplies a name and ID. Names inferred from plain text are marked accordingly. Typos, unusual ship abbreviations and conversation can produce incorrect guesses; the original message remains available. The inferred character names can be checked through public ESI name resolution; the full message text is not sent.
- `J5A-IX clr` and `J5A-IX clear` both mark the system clear and remove proximity alerts from earlier reports there.
- `J5A-IX clr?` and `clear?` are questions and do not clear previous intel. “Not clear” does not clear it either.
- Expired reports do not trigger alerts. A newer unambiguous sighting of a pilot replaces their previous system report.

Identical channel messages appearing in multiple characters' logs are deduplicated. Old lines read at startup or after selecting a new channel are marked historical and do not cause retroactive alerts. File offsets and notification acknowledgments persist locally across restarts. A new report after a clear can create a new alert episode, subject to the cooldown.

## Using the intel map

Select an own **Character** to follow. The full region of the selected character is shown by default. **Region** selects another complete region; **Follow character** returns to your character's region. Blue halos and highlighted gates mark systems within five jumps, or the distance configured in Intel settings. This is stargate distance, not a geometric circle. System placement is a schematic region diagram adjusted for label readability; gate connections follow CCP data. Distances always use the selected own character as reference, even when another system is selected. Last known Local locations use dashed highlighting and a warning rather than claiming a current live position. Drag to pan, use the wheel or +/− to zoom, and **Fit map** to restore the initial framing.

Red means an active report, green means clear, and gold marks expired intel when history is enabled. A blue ring marks a read or pinned own-character location; check its source. Labels beside systems show reported pilots. Click a system, or focus it and press Enter, to inspect original reports below. The **Intel messages** table displays up to 500 entries from the last 24 hours and supports the shared sorting and filters.

Distance uses the shortest route across the full public CCP SDE stargate network, excluding Ansiblex, wormholes and cynos. Every system in the selected region is drawn; proximity calculations still use the entire network. Public system and gate data can update with the recipe database. Chat text and intel settings stay in your local profile and are excluded from distribution packages. Original logs are never modified. File rotation, new files, UTF-16 and incomplete lines are supported.

## Activity cards, ship icons and zKillboard

Small cards beside reported systems show pilots, ships and the report age. Each report disappears from its card three minutes after the message timestamp; the card closes when no recent reports remain. The original messages remain in chat and report history, and the configured activity/alert lifetime is unchanged. Larger cards scroll internally. Ship icons use the official CCP image service. A generic “shuttle” or unrecognized ship name does not receive a guessed type ID or a fabricated type icon.

Identified pilot names open the default browser at `https://zkillboard.com/character/<ID>/`. The example for Steve Hluskan is `https://zkillboard.com/character/359618261/`. A name inferred from text remains an inference even when ESI confirms that a character of that name exists. Names without a resolved ID are marked **ID not yet identified**, with no fabricated link.

Only inferred character names are sent to the public CCP ESI resolver, without authentication tokens; full messages are not sent. Positive name–ID matches are cached locally for 30 days and negative results for one hour. Network failures do not stop log monitoring. **Refresh pilot IDs** starts any necessary lookups while respecting the cache. zKillboard opens only on a click; killboard data is not fetched in the background.

A report listing multiple pilots and ships is labelled **Multiple pilots · shared ship report**; the app does not invent a certain pilot-to-ship pairing. Ship recognition uses public EVE names and a small set of common abbreviations. Original messages remain available for verification.

## Separate map and intel chat windows

**Open map window** opens an independent, resizable Mac window with the full region, activity cards and range highlighting. **Open intel chat window** opens a game-like feed combining all selected intel channels. Each line shows its local time, channel, reporter and message. Identified pilot names link to zKillboard; selecting a system opens or focuses the map window there.

The separate map window contains only the system map, zoom controls and legend. Choose the character, region and intel options on the main Intel map page; Open map window also applies that selection to an already open map window.

On Mac, the Window menu and the app icon’s Dock context menu list the individual windows. Each window can be minimized and restored independently; automatic tab grouping is disabled.

The chat is **read-only** and never sends messages to EVE. Disable **Auto-scroll**, or scroll upwards, to retain your reading position. Returning to the bottom resumes following new messages. Messages are chronological, oldest first, with up to 500 entries from the last 24 hours. Unchanged rows are retained during background checks.

One map and one chat window can be open. Opening one again focuses the existing window. Closing an auxiliary window keeps the main app and other window running. Closing the main window or quitting stops all windows and monitoring. Theme and language are shared. Only the main window delivers OS alerts, avoiding duplicate notifications from multiple windows.

## Intel overlay

Settings → Intel settings → **Intel overlay** enables a separate borderless Mac panel. It uses the configured alert jump distance and only reliable positions and unambiguous fresh reports. It does not require OS notification permission and does not send extra notification sounds. A clear report or a pilot moving elsewhere removes the corresponding active report.

The default display duration is **60 seconds**, editable as whole seconds from 1 to 3600. Age is measured from the message timestamp, so polling or reopening the app does not restart the countdown. Older reports remain in chat. Up to five recent reports are visible at once, with system, jump distance, reported pilots, known ships and your reference character.

When empty the panel is hidden completely. In normal use it has no title bar, does not take keyboard focus and allows mouse clicks through to the underlying app. It floats above ordinary and full-screen applications; macOS system/security interfaces can take precedence.

Select a **Monitor**, **X**, **Y** and **Width**, then **Save overlay**. Coordinates are measured from that monitor’s top-left corner in screen points. Each monitor remembers its own placement. **Move overlay** displays a draggable placeholder, even without reports. Drag it onto the desired monitor and click its **Done** button. **Finish positioning · reload position** locks the panel and reads its current position back into Settings. When a saved monitor is unavailable, the panel uses an available monitor and stays within its bounds. Placement is saved locally on that Mac. Closing the app stops the overlay.
