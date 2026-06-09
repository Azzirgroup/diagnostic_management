<template>
  <div class="p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Shift Management</h1>
        <p class="text-sm text-gray-600">Shift Profiles, Opening &amp; Closing Entries</p>
      </div>
      <button
        v-if="headerAction"
        @click="headerAction.fn"
        class="flex items-center gap-2 px-4 py-2 bg-genetest-navy text-white rounded-lg hover:opacity-90 text-sm"
      >
        <FeatherIcon name="plus" class="w-4 h-4" />
        {{ headerAction.label }}
      </button>
    </div>

    <!-- Tabs -->
    <div class="bg-white rounded-lg shadow mb-4">
      <div class="border-b flex overflow-x-auto">
        <button v-for="tab in tabs" :key="tab.key" @click="switchTab(tab.key)"
          class="px-4 py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap"
          :class="activeTab === tab.key ? 'border-genetest-navy text-genetest-navy' : 'border-transparent text-gray-500 hover:text-gray-700'">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- Search & Filters (hidden on report tab) -->
    <div v-if="activeTab !== 'shift_report'" class="bg-white rounded-lg shadow mb-4">
      <div class="p-3 flex gap-4 items-center flex-wrap">
        <div class="flex-1 min-w-[250px]">
          <Input type="text" v-model="search" :placeholder="searchPlaceholder" @input="debouncedLoad" />
        </div>
        <select v-if="activeTab === 'shift_opening' || activeTab === 'shift_closing'" v-model="statusFilter" @change="loadData"
          class="border border-gray-300 rounded-md px-3 py-1.5 text-sm">
          <option value="">All Statuses</option>
          <option value="Open" v-if="activeTab === 'shift_opening'">Open</option>
          <option value="Closed" v-if="activeTab === 'shift_opening'">Closed</option>
          <option value="Draft" v-if="activeTab === 'shift_closing'">Draft</option>
          <option value="Submitted" v-if="activeTab === 'shift_closing'">Submitted</option>
          <option value="Cancelled">Cancelled</option>
        </select>
        <Button variant="outline" theme="gray" size="sm" @click="loadData" :loading="loading">
          <template #prefix><FeatherIcon name="refresh-ccw" class="w-4 h-4" /></template>Refresh
        </Button>
      </div>
    </div>

    <!-- ==================== SHIFT PROFILES TAB ==================== -->
    <div v-if="activeTab === 'shift_profiles'" class="bg-white rounded-lg shadow">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500">Loading shift profiles...</p>
      </div>
      <div v-else-if="shiftProfiles.length === 0" class="text-center py-12">
        <FeatherIcon name="briefcase" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No shift profiles found</h3>
        <p class="text-gray-500">Create a shift profile to manage payment sessions.</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profile Name</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Warehouse</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="sp in shiftProfiles" :key="sp.name" class="hover:bg-gray-50 cursor-pointer" @click="openDetail(sp, 'POS Profile')">
              <td class="px-4 py-3 text-sm font-medium text-blue-600">{{ sp.name }}</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ sp.company }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ sp.warehouse || '-' }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ sp.currency || '-' }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-1 rounded-full text-xs font-medium" :class="sp.disabled ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'">
                  {{ sp.disabled ? 'Disabled' : 'Active' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <Pagination :total="shiftProfileTotal" :pageSize="pageSize" :currentPage="currentPage" @change="handlePageChange" />
      </div>
    </div>

    <!-- ==================== SHIFT OPENING TAB ==================== -->
    <div v-if="activeTab === 'shift_opening'" class="bg-white rounded-lg shadow">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500">Loading shift opening entries...</p>
      </div>
      <div v-else-if="shiftOpenings.length === 0" class="text-center py-12">
        <FeatherIcon name="unlock" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No shift opening entries found</h3>
        <p class="text-gray-500">Open a shift to start processing payments.</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shift Profile</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cashier</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period Start</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="so in shiftOpenings" :key="so.name" class="hover:bg-gray-50 cursor-pointer" @click="openDetail(so, 'POS Opening Entry')">
              <td class="px-4 py-3 text-sm font-medium text-blue-600">{{ so.name }}</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ so.pos_profile }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ so.user }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(so.posting_date) }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ formatDatetime(so.period_start_date) }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-1 rounded-full text-xs font-medium" :class="getShiftStatusClass(so.status)">{{ so.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <Pagination :total="shiftOpeningTotal" :pageSize="pageSize" :currentPage="currentPage" @change="handlePageChange" />
      </div>
    </div>

    <!-- ==================== SHIFT CLOSING TAB ==================== -->
    <div v-if="activeTab === 'shift_closing'" class="bg-white rounded-lg shadow">
      <div v-if="loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500">Loading shift closing entries...</p>
      </div>
      <div v-else-if="shiftClosings.length === 0" class="text-center py-12">
        <FeatherIcon name="lock" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">No shift closing entries found</h3>
        <p class="text-gray-500">Close an open shift to reconcile payments.</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shift Profile</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cashier</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Grand Total</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr v-for="sc in shiftClosings" :key="sc.name" class="hover:bg-gray-50 cursor-pointer" @click="openDetail(sc, 'POS Closing Entry')">
              <td class="px-4 py-3 text-sm font-medium text-blue-600">{{ sc.name }}</td>
              <td class="px-4 py-3 text-sm text-gray-700">{{ sc.pos_profile }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ sc.user }}</td>
              <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(sc.posting_date) }}</td>
              <td class="px-4 py-3 text-sm text-gray-900 text-right font-medium">{{ formatCurrency(sc.grand_total) }}</td>
              <td class="px-4 py-3">
                <span class="px-2 py-1 rounded-full text-xs font-medium" :class="getShiftStatusClass(sc.status)">{{ sc.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <Pagination :total="shiftClosingTotal" :pageSize="pageSize" :currentPage="currentPage" @change="handlePageChange" />
      </div>
    </div>

    <!-- ==================== SHIFT REPORT TAB ==================== -->
    <div v-if="activeTab === 'shift_report'">
      <!-- Date Range & Generate -->
      <div class="bg-white rounded-lg shadow mb-4">
        <div class="p-4 flex gap-4 items-end flex-wrap">
          <div class="flex flex-col gap-1">
            <label class="text-xs font-medium text-gray-600">From Date</label>
            <input v-model="reportFromDate" type="date"
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-medium text-gray-600">To Date</label>
            <input v-model="reportToDate" type="date"
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm" />
          </div>
          <Button variant="solid" theme="blue" size="sm" @click="loadReportData"
            :loading="reportLoading" :disabled="!reportFromDate || !reportToDate">
            Generate Report
          </Button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!reportData && !reportLoading" class="bg-white rounded-lg shadow text-center py-16">
        <FeatherIcon name="bar-chart-2" class="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-700 mb-2">Shift Reconciliation Report</h3>
        <p class="text-sm text-gray-500">Select a date range and click "Generate Report" to view shift data.</p>
      </div>

      <!-- Loading -->
      <div v-if="reportLoading" class="bg-white rounded-lg shadow text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500">Generating report...</p>
      </div>

      <!-- Report Data -->
      <div v-if="reportData && !reportLoading">
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <StatCard title="Total Shifts" :value="reportData.summary.total_shifts" color="blue" icon="clock" />
          <StatCard title="Total Revenue" :value="formatCurrency(reportData.summary.total_revenue)" color="green" icon="trending-up" />
          <StatCard title="Total Variance" :value="formatCurrency(reportData.summary.total_variance)" color="amber" icon="alert-circle" />
        </div>

        <!-- Charts -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <RevenueChart :dailyTotals="reportData.daily_totals" />
          <PaymentModeChart :paymentModeTotals="reportData.payment_mode_totals" />
        </div>
        <div class="mb-4">
          <VarianceChart :dailyTotals="reportData.daily_totals" />
        </div>

        <!-- Detail Table -->
        <div class="bg-white rounded-lg shadow overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Profile</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cashier</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Closing</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Variance</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="shift in reportData.shifts" :key="shift.name" class="hover:bg-gray-50">
                <td class="px-4 py-3 text-sm font-medium text-blue-600">{{ shift.name }}</td>
                <td class="px-4 py-3 text-sm text-gray-700">{{ shift.pos_profile }}</td>
                <td class="px-4 py-3 text-sm text-gray-600">{{ shift.user }}</td>
                <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(shift.posting_date) }}</td>
                <td class="px-4 py-3 text-sm text-gray-900 text-right font-medium">{{ formatCurrency(shift.grand_total) }}</td>
                <td class="px-4 py-3 text-sm text-gray-600 text-right">{{ formatCurrency(sumRecon(shift, 'expected_amount')) }}</td>
                <td class="px-4 py-3 text-sm text-gray-600 text-right">{{ formatCurrency(sumRecon(shift, 'closing_amount')) }}</td>
                <td class="px-4 py-3 text-sm text-right font-medium"
                  :class="shift.variance < 0 ? 'text-red-600' : 'text-green-600'">
                  {{ formatCurrency(shift.variance) }}
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="reportData.shifts.length === 0" class="text-center py-8 text-sm text-gray-500">
            No submitted closing entries found for this date range.
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== CREATE SHIFT PROFILE DIALOG ==================== -->
    <Dialog v-model="showCreateProfileDialog" :options="{ title: 'New Shift Profile', size: 'xl' }">
      <template #body-main>
        <div class="p-6 max-h-[70vh] overflow-y-auto">
          <div v-if="formError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
            <div class="flex items-start gap-2">
              <FeatherIcon name="alert-circle" class="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              <div class="text-red-700">{{ formError }}</div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input v-model="profileForm.profile_name" label="Profile Name *" placeholder="e.g. Main Counter Shift" />
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Company *</label>
              <select v-model="profileForm.company" @change="onCompanyChange"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select company</option>
                <option v-for="c in companies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Warehouse *</label>
              <select v-model="profileForm.warehouse"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select warehouse</option>
                <option v-for="w in warehouses" :key="w" :value="w">{{ w }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Write Off Account *</label>
              <select v-model="profileForm.write_off_account"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select account</option>
                <option v-for="a in accounts" :key="a" :value="a">{{ a }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Write Off Cost Center *</label>
              <select v-model="profileForm.write_off_cost_center"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select cost center</option>
                <option v-for="cc in costCenters" :key="cc" :value="cc">{{ cc }}</option>
              </select>
            </div>
          </div>
          <!-- Payment Methods -->
          <div class="mt-4 border-t pt-4">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900">Payment Methods *</h4>
              <button @click="profileForm.payments.push({ mode_of_payment: '', default: 0 })" class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
                <FeatherIcon name="plus" class="w-3 h-3" />Add
              </button>
            </div>
            <div v-for="(pm, idx) in profileForm.payments" :key="idx" class="flex gap-3 mb-2 items-center">
              <select v-model="pm.mode_of_payment"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                <option value="">Select mode</option>
                <option v-for="m in modesOfPayment" :key="m" :value="m">{{ m }}</option>
              </select>
              <label class="flex items-center gap-1 text-sm text-gray-600">
                <input type="checkbox" v-model="pm.default" :true-value="1" :false-value="0" class="rounded" /> Default
              </label>
              <button v-if="profileForm.payments.length > 1" @click="profileForm.payments.splice(idx, 1)"
                class="text-red-400 hover:text-red-600"><FeatherIcon name="trash-2" class="w-4 h-4" /></button>
            </div>
          </div>
          <!-- Users -->
          <div class="mt-4 border-t pt-4">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900">Applicable Users</h4>
              <button @click="profileForm.users.push({ user: '', default: 0 })" class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
                <FeatherIcon name="plus" class="w-3 h-3" />Add
              </button>
            </div>
            <div v-for="(u, idx) in profileForm.users" :key="idx" class="flex gap-3 mb-2 items-center">
              <select v-model="u.user"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                <option value="">Select user</option>
                <option v-for="usr in users" :key="usr.name" :value="usr.name">{{ usr.full_name || usr.name }}</option>
              </select>
              <label class="flex items-center gap-1 text-sm text-gray-600">
                <input type="checkbox" v-model="u.default" :true-value="1" :false-value="0" class="rounded" /> Default
              </label>
              <button v-if="profileForm.users.length > 1" @click="profileForm.users.splice(idx, 1)"
                class="text-red-400 hover:text-red-600"><FeatherIcon name="trash-2" class="w-4 h-4" /></button>
            </div>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="showCreateProfileDialog = false" :disabled="saving">Cancel</Button>
          <Button variant="solid" theme="blue" @click="createProfile" :loading="saving"
            :disabled="!profileForm.profile_name || !profileForm.company || !profileForm.warehouse || profileForm.payments.length === 0">
            {{ saving ? 'Creating...' : 'Create Profile' }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- ==================== CREATE SHIFT OPENING DIALOG ==================== -->
    <Dialog v-model="showCreateOpeningDialog" :options="{ title: 'Open Shift', size: 'lg' }">
      <template #body-main>
        <div class="p-6">
          <div v-if="formError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
            <div class="flex items-start gap-2">
              <FeatherIcon name="alert-circle" class="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              <div class="text-red-700">{{ formError }}</div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Shift Profile *</label>
              <select v-model="openingForm.pos_profile" @change="onOpeningProfileChange"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select shift profile</option>
                <option v-for="p in posProfiles" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-sm text-gray-600 font-medium">Company *</label>
              <select v-model="openingForm.company"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select company</option>
                <option v-for="c in companies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1 md:col-span-2">
              <label class="text-sm text-gray-600 font-medium">Cashier *</label>
              <select v-model="openingForm.user"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select cashier</option>
                <option v-for="u in openingProfileUsers" :key="u.name" :value="u.name">{{ u.full_name || u.name }}</option>
              </select>
            </div>
          </div>
          <!-- Opening Balances -->
          <div class="border-t pt-4">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-semibold text-gray-900">Opening Balance</h4>
              <button @click="openingForm.balance_details.push({ mode_of_payment: '', opening_amount: 0 })"
                class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1">
                <FeatherIcon name="plus" class="w-3 h-3" />Add
              </button>
            </div>
            <div v-for="(bd, idx) in openingForm.balance_details" :key="idx" class="flex gap-3 mb-2 items-center">
              <select v-model="bd.mode_of_payment"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                <option value="">Select mode</option>
                <option v-for="m in modesOfPayment" :key="m" :value="m">{{ m }}</option>
              </select>
              <input v-model.number="bd.opening_amount" type="number" min="0" step="0.01" placeholder="0.00"
                class="w-32 px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              <button v-if="openingForm.balance_details.length > 1" @click="openingForm.balance_details.splice(idx, 1)"
                class="text-red-400 hover:text-red-600"><FeatherIcon name="trash-2" class="w-4 h-4" /></button>
            </div>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="showCreateOpeningDialog = false" :disabled="saving">Cancel</Button>
          <Button variant="solid" theme="blue" @click="createOpening" :loading="saving"
            :disabled="!openingForm.pos_profile || !openingForm.company || !openingForm.user">
            {{ saving ? 'Opening...' : 'Open Shift' }}
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- ==================== CREATE SHIFT CLOSING DIALOG ==================== -->
    <Dialog v-model="showCreateClosingDialog" :options="{ title: 'Close Shift', size: 'xl' }">
      <template #body-main>
        <div class="p-6 max-h-[70vh] overflow-y-auto">
          <div v-if="formError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
            <div class="flex items-start gap-2">
              <FeatherIcon name="alert-circle" class="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              <div class="text-red-700">{{ formError }}</div>
            </div>
          </div>
          <div v-if="openShiftEntries.length === 0 && !closingPreviewLoading" class="text-center py-6">
            <FeatherIcon name="info" class="h-8 w-8 text-gray-400 mx-auto mb-3" />
            <p class="text-gray-600">No open shifts found for your user. Open a shift first.</p>
          </div>
          <div v-else>
            <div class="flex flex-col gap-1 mb-4">
              <label class="text-sm text-gray-600 font-medium">Open Shift *</label>
              <select v-model="closingForm.pos_opening_entry" @change="onClosingEntryChange"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                <option value="">Select open shift</option>
                <option v-for="oe in openShiftEntries" :key="oe.name" :value="oe.name">
                  {{ oe.pos_profile }} - {{ oe.user }} - {{ formatDatetime(oe.period_start_date) }}
                </option>
              </select>
            </div>

            <!-- Loading preview -->
            <div v-if="closingPreviewLoading" class="text-center py-6">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-3"></div>
              <p class="text-sm text-gray-500">Loading shift data...</p>
            </div>

            <!-- Preview data -->
            <div v-if="closingPreview && !closingPreviewLoading">
              <!-- Summary -->
              <div class="grid grid-cols-3 gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
                <div>
                  <p class="text-xs text-gray-500">Invoices</p>
                  <p class="text-lg font-bold text-gray-900">{{ closingPreview.invoice_count }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500">Grand Total</p>
                  <p class="text-lg font-bold text-gray-900">{{ formatCurrency(closingPreview.grand_total) }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500">Total Qty</p>
                  <p class="text-lg font-bold text-gray-900">{{ closingPreview.total_qty }}</p>
                </div>
              </div>

              <!-- Payment Reconciliation -->
              <div class="border-t pt-4">
                <h4 class="text-sm font-semibold text-gray-900 mb-3">Payment Reconciliation</h4>
                <div v-if="closingForm.closing_details.length === 0" class="text-sm text-gray-500 py-3">
                  No payment modes found for this shift.
                </div>
                <table v-else class="w-full text-sm">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Mode of Payment</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Opening</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Expected</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Closing *</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Difference</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y">
                    <tr v-for="(cd, idx) in closingForm.closing_details" :key="idx">
                      <td class="px-3 py-2 text-gray-700">{{ cd.mode_of_payment }}</td>
                      <td class="px-3 py-2 text-right text-gray-600">{{ formatCurrency(cd.opening_amount) }}</td>
                      <td class="px-3 py-2 text-right text-gray-600">{{ formatCurrency(cd.expected_amount) }}</td>
                      <td class="px-3 py-2 text-right">
                        <input v-model.number="cd.closing_amount" type="number" min="0" step="0.01"
                          class="w-28 px-2 py-1 border border-gray-300 rounded text-sm text-right" />
                      </td>
                      <td class="px-3 py-2 text-right font-medium"
                        :class="(cd.closing_amount - cd.expected_amount) < 0 ? 'text-red-600' : 'text-green-600'">
                        {{ formatCurrency(cd.closing_amount - cd.expected_amount) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Invoices list -->
              <div v-if="closingPreview.invoices && closingPreview.invoices.length" class="border-t pt-4 mt-4">
                <h4 class="text-sm font-semibold text-gray-900 mb-3">Invoices in this Shift</h4>
                <table class="w-full text-sm">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Invoice</th>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Customer</th>
                      <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Date</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Total</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y">
                    <tr v-for="inv in closingPreview.invoices" :key="inv.name">
                      <td class="px-3 py-2 text-blue-600 font-medium">{{ inv.name }}</td>
                      <td class="px-3 py-2 text-gray-700">{{ inv.customer_name }}</td>
                      <td class="px-3 py-2 text-gray-600">{{ formatDate(inv.posting_date) }}</td>
                      <td class="px-3 py-2 text-right text-gray-900 font-medium">{{ formatCurrency(inv.grand_total) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="showCreateClosingDialog = false" :disabled="saving">Cancel</Button>
          <Button v-if="openShiftEntries.length > 0 && closingPreview" variant="solid" theme="blue"
            @click="createClosing(false)" :loading="saving && !submitMode"
            :disabled="!closingForm.pos_opening_entry || saving">
            Save as Draft
          </Button>
          <button v-if="openShiftEntries.length > 0 && closingPreview"
            @click="createClosing(true)"
            :disabled="!closingForm.pos_opening_entry || saving"
            class="px-4 py-1.5 rounded-md text-sm font-medium text-white disabled:opacity-50" style="background-color: #16a34a;">
            {{ (saving && submitMode) ? 'Closing...' : 'Close & Submit' }}
          </button>
        </div>
      </template>
    </Dialog>

    <!-- ==================== VIEW DETAIL DIALOG ==================== -->
    <Dialog v-model="showDetailDialog" :options="{ title: detailRecord ? detailRecord.name : 'Detail', size: 'xl' }">
      <template #body-main>
        <div class="p-6" v-if="detailRecord">
          <!-- Error display -->
          <div v-if="detailError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
            <div class="flex items-start gap-2">
              <FeatherIcon name="alert-circle" class="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              <div class="text-red-700">{{ detailError }}</div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1" v-for="field in detailFields" :key="field.key">
              <label class="text-sm text-gray-600 font-medium">{{ field.label }}</label>
              <div class="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700">
                <span v-if="field.type === 'currency'">{{ formatCurrency(detailRecord[field.key]) }}</span>
                <span v-else-if="field.type === 'date'">{{ formatDate(detailRecord[field.key]) }}</span>
                <span v-else-if="field.type === 'datetime'">{{ formatDatetime(detailRecord[field.key]) }}</span>
                <span v-else-if="field.type === 'status'" class="px-2 py-1 rounded-full text-xs font-medium"
                  :class="field.statusClass(detailRecord[field.key])">
                  {{ detailRecord[field.key] || '-' }}
                </span>
                <span v-else>{{ detailRecord[field.key] || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- Shift Profile Payment Methods -->
          <div v-if="detailDoctype === 'POS Profile' && detailRecord.payments && detailRecord.payments.length" class="mt-6 border-t pt-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">Payment Methods</h4>
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Mode of Payment</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Default</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="pm in detailRecord.payments" :key="pm.name">
                  <td class="px-3 py-2 text-gray-700">{{ pm.mode_of_payment }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ pm.default ? 'Yes' : 'No' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Shift Profile Users -->
          <div v-if="detailDoctype === 'POS Profile' && detailRecord.applicable_for_users && detailRecord.applicable_for_users.length" class="mt-4 border-t pt-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">Applicable Users</h4>
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">User</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Default</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="u in detailRecord.applicable_for_users" :key="u.name">
                  <td class="px-3 py-2 text-gray-700">{{ u.user }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ u.default ? 'Yes' : 'No' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Shift Opening Balance Details -->
          <div v-if="detailDoctype === 'POS Opening Entry' && detailRecord.balance_details && detailRecord.balance_details.length" class="mt-6 border-t pt-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">Opening Balance</h4>
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Mode of Payment</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Opening Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="bd in detailRecord.balance_details" :key="bd.name">
                  <td class="px-3 py-2 text-gray-700">{{ bd.mode_of_payment }}</td>
                  <td class="px-3 py-2 text-right text-gray-900 font-medium">{{ formatCurrency(bd.opening_amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Shift Closing Payment Reconciliation -->
          <div v-if="detailDoctype === 'POS Closing Entry' && detailRecord.payment_reconciliation && detailRecord.payment_reconciliation.length" class="mt-6 border-t pt-4">
            <h4 class="text-sm font-semibold text-gray-900 mb-3">Payment Reconciliation</h4>
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500">Mode of Payment</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Opening</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Expected</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Closing</th>
                  <th class="px-3 py-2 text-right text-xs font-medium text-gray-500">Difference</th>
                </tr>
              </thead>
              <tbody class="divide-y">
                <tr v-for="cd in detailRecord.payment_reconciliation" :key="cd.name">
                  <td class="px-3 py-2 text-gray-700">{{ cd.mode_of_payment }}</td>
                  <td class="px-3 py-2 text-right text-gray-600">{{ formatCurrency(cd.opening_amount) }}</td>
                  <td class="px-3 py-2 text-right text-gray-600">{{ formatCurrency(cd.expected_amount) }}</td>
                  <td class="px-3 py-2 text-right text-gray-900 font-medium">{{ formatCurrency(cd.closing_amount) }}</td>
                  <td class="px-3 py-2 text-right" :class="cd.difference < 0 ? 'text-red-600 font-medium' : 'text-green-600'">
                    {{ formatCurrency(cd.difference) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Submit button for Draft entries -->
          <div v-if="Number(detailRecord.docstatus) === 0 && (detailDoctype === 'POS Closing Entry' || detailDoctype === 'POS Opening Entry')"
            class="mt-6 border-t pt-4">
            <button @click="submitDetail" :disabled="saving"
              class="w-full px-4 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-50 bg-green-600 hover:bg-green-700">
              {{ saving ? 'Submitting...' : 'Submit' }}
            </button>
          </div>
        </div>
        <div v-else class="p-6 text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p class="text-gray-500">Loading...</p>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <button v-if="detailRecord && Number(detailRecord.docstatus) === 0"
            @click="submitDetail" :disabled="saving"
            class="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 bg-green-600 hover:bg-green-700">
            {{ saving ? 'Submitting...' : 'Submit' }}
          </button>
          <Button variant="outline" @click="showDetailDialog = false">Close</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { call } from 'frappe-ui'
import { Button, Input, FeatherIcon, Dialog } from 'frappe-ui'
import Pagination from '@/components/common/Pagination.vue'
import StatCard from '@/components/common/StatCard.vue'
import RevenueChart from '@/components/common/RevenueChart.vue'
import PaymentModeChart from '@/components/common/PaymentModeChart.vue'
import VarianceChart from '@/components/common/VarianceChart.vue'

const activeTab = ref('shift_profiles')
const search = ref('')
const statusFilter = ref('')
const loading = ref(false)
const saving = ref(false)
const submitMode = ref(false)
const currentPage = ref(1)
const pageSize = 25
const formError = ref('')

const tabs = [
  { key: 'shift_profiles', label: 'Shift Profiles' },
  { key: 'shift_opening', label: 'Shift Opening' },
  { key: 'shift_closing', label: 'Shift Closing' },
  { key: 'shift_report', label: 'Shift Report' },
]

// Shift Report state
const reportFromDate = ref('')
const reportToDate = ref('')
const reportData = ref(null)
const reportLoading = ref(false)

async function loadReportData() {
  if (!reportFromDate.value || !reportToDate.value) return
  reportLoading.value = true
  reportData.value = null
  try {
    reportData.value = await call('diagnostic_management.api.shifts.get_shift_report_data', {
      from_date: reportFromDate.value,
      to_date: reportToDate.value,
    })
  } catch (err) { console.error('Failed to load report:', err) }
  finally { reportLoading.value = false }
}

// Data
const shiftProfiles = ref([])
const shiftProfileTotal = ref(0)
const shiftOpenings = ref([])
const shiftOpeningTotal = ref(0)
const shiftClosings = ref([])
const shiftClosingTotal = ref(0)

// Lookups
const modesOfPayment = ref([])
const posProfiles = ref([])
const companies = ref([])
const warehouses = ref([])
const accounts = ref([])
const costCenters = ref([])
const users = ref([])
const openShiftEntries = ref([])
const loggedInUser = ref('')

// Closing preview
const closingPreview = ref(null)
const closingPreviewLoading = ref(false)

// Dialogs
const showCreateProfileDialog = ref(false)
const showCreateOpeningDialog = ref(false)
const showCreateClosingDialog = ref(false)
const showDetailDialog = ref(false)
const detailRecord = ref(null)
const detailDoctype = ref('')
const detailError = ref('')

// Forms
const profileForm = ref({
  profile_name: '', company: '', warehouse: '', write_off_account: '', write_off_cost_center: '',
  payments: [{ mode_of_payment: '', default: 0 }], users: [],
})
const openingForm = ref({ pos_profile: '', company: '', user: '', balance_details: [{ mode_of_payment: '', opening_amount: 0 }] })
const openingProfileUsers = ref([])
const closingForm = ref({ pos_opening_entry: '', closing_details: [] })

// Computeds
const searchPlaceholder = computed(() => {
  const map = {
    shift_profiles: 'Search shift profiles...',
    shift_opening: 'Search shift openings...',
    shift_closing: 'Search shift closings...',
  }
  return map[activeTab.value] || 'Search...'
})

const headerAction = computed(() => {
  const map = {
    shift_profiles: { label: 'New Shift Profile', fn: openCreateProfile },
    shift_opening: { label: 'New POS Opening Entry', fn: openCreateOpening },
    shift_closing: { label: 'New POS Closing Entry', fn: openCreateClosing },
  }
  return map[activeTab.value] || null
})

const detailFields = computed(() => {
  if (detailDoctype.value === 'POS Profile') {
    return [
      { key: 'name', label: 'Profile Name' },
      { key: 'company', label: 'Company' },
      { key: 'warehouse', label: 'Warehouse' },
      { key: 'currency', label: 'Currency' },
      { key: 'write_off_account', label: 'Write Off Account' },
      { key: 'write_off_cost_center', label: 'Write Off Cost Center' },
    ]
  }
  if (detailDoctype.value === 'POS Opening Entry') {
    return [
      { key: 'name', label: 'Entry ID' },
      { key: 'pos_profile', label: 'Shift Profile' },
      { key: 'user', label: 'Cashier' },
      { key: 'company', label: 'Company' },
      { key: 'posting_date', label: 'Posting Date', type: 'date' },
      { key: 'period_start_date', label: 'Period Start', type: 'datetime' },
      { key: 'status', label: 'Status', type: 'status', statusClass: getShiftStatusClass },
    ]
  }
  if (detailDoctype.value === 'POS Closing Entry') {
    return [
      { key: 'name', label: 'Entry ID' },
      { key: 'pos_profile', label: 'Shift Profile' },
      { key: 'user', label: 'Cashier' },
      { key: 'company', label: 'Company' },
      { key: 'posting_date', label: 'Posting Date', type: 'date' },
      { key: 'period_start_date', label: 'Period Start', type: 'datetime' },
      { key: 'period_end_date', label: 'Period End', type: 'datetime' },
      { key: 'grand_total', label: 'Grand Total', type: 'currency' },
      { key: 'net_total', label: 'Net Total', type: 'currency' },
      { key: 'total_quantity', label: 'Total Quantity' },
      { key: 'status', label: 'Status', type: 'status', statusClass: getShiftStatusClass },
    ]
  }
  return []
})

// Tab switching
function switchTab(key) { activeTab.value = key }

// Load data
let debounceTimer = null
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { currentPage.value = 1; loadData() }, 300)
}

async function loadData() {
  loading.value = true
  try {
    if (activeTab.value === 'shift_profiles') {
      const res = await call('diagnostic_management.api.shifts.get_shift_profiles', {
        search: search.value, limit: pageSize, start: (currentPage.value - 1) * pageSize
      })
      shiftProfiles.value = res.data || []; shiftProfileTotal.value = res.total || 0
    } else if (activeTab.value === 'shift_opening') {
      const res = await call('diagnostic_management.api.shifts.get_shift_opening_entries', {
        search: search.value, status: statusFilter.value,
        limit: pageSize, start: (currentPage.value - 1) * pageSize
      })
      shiftOpenings.value = res.data || []; shiftOpeningTotal.value = res.total || 0
    } else if (activeTab.value === 'shift_closing') {
      const res = await call('diagnostic_management.api.shifts.get_shift_closing_entries', {
        search: search.value, status: statusFilter.value,
        limit: pageSize, start: (currentPage.value - 1) * pageSize
      })
      shiftClosings.value = res.data || []; shiftClosingTotal.value = res.total || 0
    }
  } catch (err) { console.error('Failed to load data:', err) }
  finally { loading.value = false }
}

function handlePageChange(page) { currentPage.value = page; loadData() }

// Lookups
async function loadModesOfPayment() {
  try { modesOfPayment.value = await call('diagnostic_management.api.shifts.get_modes_of_payment') || [] } catch (err) { console.error(err) }
}
async function loadPosProfiles() {
  try { posProfiles.value = await call('diagnostic_management.api.shifts.get_pos_profiles') || [] } catch (err) { console.error(err) }
}
async function loadCompanies() {
  try { companies.value = await call('diagnostic_management.api.shifts.get_companies') || [] } catch (err) { console.error(err) }
}
async function loadUsers() {
  try { users.value = await call('diagnostic_management.api.shifts.get_users') || [] } catch (err) { console.error(err) }
}
async function loadOpenShiftEntries() {
  try { openShiftEntries.value = await call('diagnostic_management.api.shifts.get_open_shift_entries') || [] } catch (err) { console.error(err) }
}
async function loadLoggedInUser() {
  try { loggedInUser.value = await call('frappe.auth.get_logged_user') } catch (err) { console.error(err) }
}

async function onCompanyChange() {
  const company = profileForm.value.company
  if (!company) { warehouses.value = []; accounts.value = []; costCenters.value = []; return }
  try {
    const [wh, acc, cc] = await Promise.all([
      call('diagnostic_management.api.shifts.get_warehouses', { company }),
      call('diagnostic_management.api.shifts.get_accounts', { company }),
      call('diagnostic_management.api.shifts.get_cost_centers', { company }),
    ])
    warehouses.value = wh || []; accounts.value = acc || []; costCenters.value = cc || []
  } catch (err) { console.error(err) }
}

async function onOpeningProfileChange() {
  openingProfileUsers.value = []
  openingForm.value.user = ''
  if (!openingForm.value.pos_profile) return
  try {
    const profile = await call('diagnostic_management.api.shifts.get_record_detail', {
      doctype: 'POS Profile', name: openingForm.value.pos_profile
    })
    if (profile.company) openingForm.value.company = profile.company
    if (profile.payments && profile.payments.length) {
      openingForm.value.balance_details = profile.payments.map(pm => ({
        mode_of_payment: pm.mode_of_payment, opening_amount: 0,
      }))
    }
    // Load all system users for cashier selection
    if (!users.value.length) await loadUsers()
    openingProfileUsers.value = users.value
    // Default to current logged-in user
    if (loggedInUser.value) {
      const match = openingProfileUsers.value.find(u => u.name === loggedInUser.value)
      if (match) openingForm.value.user = match.name
    }
  } catch (err) { console.error(err) }
}

async function onClosingEntryChange() {
  closingPreview.value = null
  closingForm.value.closing_details = []
  if (!closingForm.value.pos_opening_entry) return
  closingPreviewLoading.value = true
  try {
    const preview = await call('diagnostic_management.api.shifts.get_shift_closing_preview', {
      pos_opening_entry: closingForm.value.pos_opening_entry
    })
    closingPreview.value = preview
    closingForm.value.closing_details = (preview.reconciliation || []).map(r => ({
      mode_of_payment: r.mode_of_payment,
      opening_amount: r.opening_amount,
      expected_amount: r.expected_amount,
      closing_amount: 0,
    }))
  } catch (err) { formError.value = extractError(err) }
  finally { closingPreviewLoading.value = false }
}

// Open dialogs
function openCreateProfile() {
  profileForm.value = { profile_name: '', company: '', warehouse: '', write_off_account: '', write_off_cost_center: '',
    payments: [{ mode_of_payment: '', default: 0 }], users: [] }
  formError.value = ''; showCreateProfileDialog.value = true
  loadCompanies(); loadUsers()
}
async function openCreateOpening() {
  openingForm.value = { pos_profile: '', company: '', user: '', balance_details: [{ mode_of_payment: '', opening_amount: 0 }] }
  formError.value = ''; showCreateOpeningDialog.value = true
  loadCompanies()
  if (!users.value.length) await loadUsers()
  openingProfileUsers.value = users.value
  // Auto-select current user
  if (loggedInUser.value) {
    const match = users.value.find(u => u.name === loggedInUser.value)
    if (match) openingForm.value.user = match.name
  }
}
function openCreateClosing() {
  closingForm.value = { pos_opening_entry: '', closing_details: [] }
  closingPreview.value = null; closingPreviewLoading.value = false
  formError.value = ''; showCreateClosingDialog.value = true
  loadOpenShiftEntries()
}

// Create actions
async function createProfile() {
  formError.value = ''; saving.value = true
  try {
    await call('diagnostic_management.api.shifts.create_shift_profile', {
      name: profileForm.value.profile_name,
      company: profileForm.value.company,
      warehouse: profileForm.value.warehouse,
      write_off_account: profileForm.value.write_off_account,
      write_off_cost_center: profileForm.value.write_off_cost_center,
      payments: JSON.stringify(profileForm.value.payments.filter(p => p.mode_of_payment)),
      applicable_for_users: JSON.stringify(profileForm.value.users.filter(u => u.user)),
    })
    showCreateProfileDialog.value = false; loadData(); loadPosProfiles()
  } catch (err) { formError.value = extractError(err) } finally { saving.value = false }
}

async function createOpening() {
  formError.value = ''; saving.value = true
  try {
    await call('diagnostic_management.api.shifts.create_shift_opening_entry', {
      pos_profile: openingForm.value.pos_profile,
      company: openingForm.value.company,
      user: openingForm.value.user,
      balance_details: JSON.stringify(openingForm.value.balance_details.filter(b => b.mode_of_payment)),
    })
    showCreateOpeningDialog.value = false; loadData()
  } catch (err) { formError.value = extractError(err) } finally { saving.value = false }
}

async function createClosing(submit = false) {
  formError.value = ''; saving.value = true; submitMode.value = submit
  try {
    await call('diagnostic_management.api.shifts.create_shift_closing_entry', {
      pos_opening_entry: closingForm.value.pos_opening_entry,
      closing_details: JSON.stringify(closingForm.value.closing_details.filter(c => c.mode_of_payment)),
      do_submit: submit ? 1 : 0
    })
    showCreateClosingDialog.value = false; loadData()
  } catch (err) { formError.value = extractError(err) } finally { saving.value = false; submitMode.value = false }
}

// Detail dialog
async function openDetail(record, doctype) {
  detailError.value = ''; detailRecord.value = null; detailDoctype.value = doctype; showDetailDialog.value = true
  try { detailRecord.value = await call('diagnostic_management.api.shifts.get_record_detail', { doctype, name: record.name }) }
  catch (err) { detailError.value = extractError(err) }
}

async function submitDetail() {
  if (!detailRecord.value) return
  detailError.value = ''; saving.value = true
  try {
    await call('diagnostic_management.api.shifts.submit_document', { doctype: detailDoctype.value, name: detailRecord.value.name })
    detailRecord.value.docstatus = 1
    detailRecord.value.status = 'Submitted'
    loadData()
  } catch (err) { detailError.value = extractError(err) } finally { saving.value = false }
}

// Formatters
function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
function formatDatetime(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function formatCurrency(v) {
  if (v == null) return '-'
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES' }).format(v)
}

function sumRecon(shift, field) {
  if (!shift.reconciliation) return 0
  return shift.reconciliation.reduce((sum, r) => sum + (r[field] || 0), 0)
}

function getShiftStatusClass(status) {
  const map = { 'Open': 'bg-green-100 text-green-700', 'Closed': 'bg-gray-100 text-gray-700',
    'Draft': 'bg-yellow-100 text-yellow-700', 'Submitted': 'bg-green-100 text-green-700',
    'Queued': 'bg-blue-100 text-blue-700', 'Failed': 'bg-red-100 text-red-700', 'Cancelled': 'bg-red-100 text-red-700' }
  return map[status] || 'bg-gray-100 text-gray-700'
}

function extractError(err) {
  if (err.messages && err.messages.length) return err.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
  return err.message || 'An error occurred'
}

watch(activeTab, () => { search.value = ''; statusFilter.value = ''; currentPage.value = 1; loadData() })
onMounted(() => { loadData(); loadModesOfPayment(); loadPosProfiles(); loadLoggedInUser() })
</script>
