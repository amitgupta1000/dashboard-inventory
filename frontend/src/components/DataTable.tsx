import { useMemo } from 'react';
import { useTable, useSortBy, usePagination, Column } from 'react-table';

interface InventoryItem {
  company_name: string;
  port_name: string;
  product_name: string;
  physical_stock: number;
  total_sold_qty: number;
  total_unsold_qty: number;
  incoming_vessel_qty: number | string;
  avg_import_price_usd: number;
  avg_price_inr: number;
  current_market_price: number | string;
  replacement_cost: number | string;
  stock_value: number;
}

interface DataTableProps {
  data: InventoryItem[];
}

const DataTable: React.FC<DataTableProps> = ({ data }) => {
  const columns: Column<InventoryItem>[] = useMemo(
    () => [
      {
        Header: 'Company Name',
        accessor: 'company_name',
      },
      {
        Header: 'Port Name',
        accessor: 'port_name',
      },
      {
        Header: 'Product',
        accessor: 'product_name',
      },
      {
        Header: 'Physical Stock',
        accessor: 'physical_stock',
        Cell: ({ value }) => (
          <span>
            {typeof value === 'number'
              ? value.toLocaleString('en-US', { maximumFractionDigits: 3 })
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Total Sold Qty',
        accessor: 'total_sold_qty',
        Cell: ({ value }) => (
          <span>
            {typeof value === 'number'
              ? value.toLocaleString('en-US', { maximumFractionDigits: 3 })
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Total Unsold Qty',
        accessor: 'total_unsold_qty',
        Cell: ({ value }) => (
          <span>
            {typeof value === 'number'
              ? value.toLocaleString('en-US', { maximumFractionDigits: 3 })
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Incoming Vessel Qty',
        accessor: 'incoming_vessel_qty',
        Cell: ({ value }) => (
          <span>
            {typeof value === 'number'
              ? value.toLocaleString('en-US', { maximumFractionDigits: 3 })
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Avg Import Price (USD)',
        accessor: 'avg_import_price_usd',
        Cell: ({ value }) => (
          <span className="font-semibold">
            {typeof value === 'number'
              ? `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Avg Price (INR) / MT',
        accessor: 'avg_price_inr',
        Cell: ({ value }) => (
          <span className="font-semibold text-green-600">
            {typeof value === 'number'
              ? `₹${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : value || '-'}
          </span>
        ),
      },
      {
        Header: 'Stock Value (INR)',
        accessor: 'stock_value',
        Cell: ({ value }) => (
          <span className="font-bold text-green-600">
            {typeof value === 'number'
              ? `₹${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : value || '-'}
          </span>
        ),
      },
    ],
    []
  );

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    page,
    prepareRow,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    setPageSize,
    state: { pageIndex, pageSize },
  } = useTable<InventoryItem>(
    {
      columns,
      data,
      initialState: { pageIndex: 0, pageSize: 10 },
    },
    useSortBy,
    usePagination
  );

  return (
    <div className="bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto rounded-t-2xl">
        <table {...getTableProps()} className="w-full text-left">
          <thead className="bg-gradient-to-r from-slate-100 to-slate-50 border-b-2 border-slate-200">
            {headerGroups.map((headerGroup) => (
              <tr {...headerGroup.getHeaderGroupProps()}>
                {headerGroup.headers.map((column, idx) => (
                  <th
                    {...column.getHeaderProps((column as any).getSortByToggleProps())}
                    className={`px-6 py-4 text-xs font-bold text-slate-600 uppercase tracking-wider cursor-pointer hover:bg-slate-200 transition-colors ${
                      idx === 0 ? 'rounded-tl-lg' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {column.render('Header')}
                      <span className="text-sm">
                        {(column as any).isSorted
                          ? (column as any).isSortedDesc
                            ? '📉'
                            : '📈'
                          : ''}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody {...getTableBodyProps()} className="divide-y divide-slate-100">
            {page.map((row, i) => {
              prepareRow(row);
              return (
                <tr
                  {...row.getRowProps()}
                  className="hover:bg-gradient-to-r hover:from-slate-50 hover:to-blue-50/30 transition-all duration-200"
                >
                  {row.cells.map((cell) => (
                    <td
                      {...cell.getCellProps()}
                      className="px-6 py-4 text-sm text-slate-700 font-medium"
                    >
                      {cell.render('Cell')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="bg-gradient-to-r from-slate-50 to-blue-50/30 px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-4 border-t border-slate-200">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-700">Page</span>
            <strong className="text-slate-800">
              {pageIndex + 1} of {pageOptions.length}
            </strong>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-700">Go to:</span>
            <input
              type="number"
              defaultValue={pageIndex + 1}
              onChange={(e) => {
                const page = e.target.value ? Number(e.target.value) - 1 : 0;
                gotoPage(page);
              }}
              className="w-16 px-3 py-2 border-2 border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-medium"
            />
          </div>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
            }}
            className="px-3 py-2 border-2 border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold"
          >
            {[10, 20, 30, 50].map((pageSize) => (
              <option key={pageSize} value={pageSize}>
                Show {pageSize}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => gotoPage(0)}
            disabled={!canPreviousPage}
            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-lg disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed hover:shadow-lg transition-all text-sm"
            title="First page"
          >
            ⬅️ First
          </button>
          <button
            onClick={() => previousPage()}
            disabled={!canPreviousPage}
            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-lg disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed hover:shadow-lg transition-all text-sm"
            title="Previous page"
          >
            ◀ Prev
          </button>
          <button
            onClick={() => nextPage()}
            disabled={!canNextPage}
            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-lg disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed hover:shadow-lg transition-all text-sm"
            title="Next page"
          >
            Next ▶
          </button>
          <button
            onClick={() => gotoPage(pageCount - 1)}
            disabled={!canNextPage}
            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-bold rounded-lg disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed hover:shadow-lg transition-all text-sm"
            title="Last page"
          >
            Last ➡️
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
