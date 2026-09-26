import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import clsx from "clsx";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { useState } from "react";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    align?: "left" | "right";
  }
}

/** Sortable table. Scrolls horizontally inside its card on narrow screens. */
export function DataTable<T>({ data, columns, initialSort = [], onRowClick, dense = false, caption }: {
  data: T[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<T, any>[];
  initialSort?: SortingState;
  onRowClick?: (row: T) => void;
  dense?: boolean;
  caption?: string;
}) {
  const [sorting, setSorting] = useState<SortingState>(initialSort);
  // TanStack Table returns non-memoizable functions by design.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="-mx-5 overflow-x-auto px-5">
      <table className="tabular w-full border-collapse text-[14px]">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id} className="border-b border-hairline">
              {group.headers.map((header) => {
                const right = header.column.columnDef.meta?.align === "right";
                const sorted = header.column.getIsSorted();
                return (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                    className={clsx("px-3 py-2.5 text-[12px] font-semibold tracking-[0.3px] whitespace-nowrap text-steel uppercase first:pl-0",
                      right ? "text-right" : "text-left")}
                  >
                    {header.isPlaceholder ? null : header.column.getCanSort() ? (
                      <button
                        onClick={header.column.getToggleSortingHandler()}
                        className={clsx("inline-flex items-center gap-1 uppercase hover:text-ink", right && "flex-row-reverse")}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sorted === "asc" ? <ArrowUp className="size-3" aria-hidden /> :
                          sorted === "desc" ? <ArrowDown className="size-3" aria-hidden /> :
                            <ArrowUpDown className="size-3 opacity-40" aria-hidden />}
                      </button>
                    ) : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={onRowClick ? () => onRowClick(row.original) : undefined}
              className={clsx("border-b border-hairline-soft last:border-0", onRowClick && "cursor-pointer hover:bg-surface-soft")}
            >
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className={clsx("px-3 whitespace-nowrap first:pl-0", dense ? "py-2" : "py-3",
                    cell.column.columnDef.meta?.align === "right" ? "text-right" : "text-left")}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && <div className="py-8 text-center text-[14px] text-steel">No rows match.</div>}
    </div>
  );
}
