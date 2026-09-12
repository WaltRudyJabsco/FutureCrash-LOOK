# Future Crash + LOOK 1.6.15

LOOK's interactive filer can now hand its selected working set directly to LO.

Filter/select normally, mark paths with `Tab` or `A`, then press **`L`**. If nothing is marked, the highlighted path is handed off. LO opens with an explicit path manifest and reports the count in its startup banner.

The handoff does not preload file contents. LO uses its existing bounded file tools only when needed. Its workspace is rooted at the nearest common selected directory so every handed-off path remains inside the accessible tool boundary.

LOOK is 3.10.4. Future Crash remains 1.1.7.
