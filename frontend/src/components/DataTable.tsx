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
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table {...getTableProps()} className="w-full">
          <thead className="bg-blue-500">
            {headerGroups.map((headerGroup) => (
              <tr {...headerGroup.getHeaderGroupProps()}>
                {headerGroup.headers.map((column) => (
                  <th
                    {...column.getHeaderProps((column as any).getSortByToggleProps())}
                    className="px-4 py-4 text-left text-sm font-semibold text-white cursor-pointer hover:bg-blue-600"
                  >
                    <div className="flex items-center gap-2">
                      {column.render('Header')}
                      <span className="text-xs">
                        {(column as any).isSorted
                          ? (column as any).isSortedDesc
                            ? ' 🔽'
                            : ' 🔼'
                          : ''}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody {...getTableBodyProps()}>
            {page.map((row, i) => {
              prepareRow(row);
              return (
                <tr
                  {...row.getRowProps()}
                  className={`${
                    i % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                  } hover:bg-blue-50 transition-colors`}
                >
                  {row.cells.map((cell) => (
                    <td
                      {...cell.getCellProps()}
                      className="px-4 py-4 text-sm text-gray-700 border-b border-gray-200"
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
      <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-700">
            Page{' '}
            <strong>
              {pageIndex + 1} of {pageOptions.length}
            </strong>
          </span>
          <span className="text-sm text-gray-700">
            | Go to page:{' '}
            <input
              type="number"
              defaultValue={pageIndex + 1}
              onChange={(e) => {
                const page = e.target.value ? Number(e.target.value) - 1 : 0;
                gotoPage(page);
              }}
              className="w-16 px-2 py-1 border border-gray-300 rounded"
            />
          </span>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
            }}
            className="px-2 py-1 border border-gray-300 rounded text-sm"
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
            className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600"
          >
            {'<<'}
          </button>
          <button
            onClick={() => previousPage()}
            disabled={!canPreviousPage}
            className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600"
          >
            {'<'}
          </button>
          <button
            onClick={() => nextPage()}
            disabled={!canNextPage}
            className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600"
          >
            {'>'}
          </button>
          <button
            onClick={() => gotoPage(pageCount - 1)}
            disabled={!canNextPage}
            className="px-3 py-1 bg-blue-500 text-white rounded disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600"
          >
            {'>>'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
