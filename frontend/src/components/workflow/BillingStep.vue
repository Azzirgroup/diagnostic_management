<template>
  <div class="step-content max-w-7xl mx-auto px-4">
    <SectionHeader
      :section-number="2"
      title="Billing & Insurance"
      :description="showPaymentForm ? 'Complete payment for the created invoice' : 'Select payment type and confirm billing details'"
      color="green"
    />

    <!-- ═══ PAYMENT ENTRY FORM (shown after invoice created + user clicked Continue to Payment) ═══ -->
    <template v-if="showPaymentForm && createdInvoice">
      <!-- Invoice Summary -->
      <div class="bg-green-50 border border-green-200 rounded-xl p-5 mb-6">
        <div class="flex items-start gap-3 mb-3">
          <FeatherIcon name="check-circle" class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-semibold text-green-800">Sales Invoice Created: {{ createdInvoice.invoice_id }}</p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
          <div class="bg-white rounded-lg p-3">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Invoice</p>
            <p class="text-sm font-semibold text-gray-900 mt-1">{{ createdInvoice.invoice_id }}</p>
          </div>
          <div class="bg-white rounded-lg p-3">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Customer</p>
            <p class="text-sm font-semibold text-gray-900 mt-1">{{ billingInfo.customer_name || billingInfo.customer }}</p>
          </div>
          <div class="bg-white rounded-lg p-3">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Grand Total</p>
            <p class="text-sm font-semibold text-gray-900 mt-1">{{ formatCurrency(createdInvoice.grand_total || totalAmount) }}</p>
          </div>
        </div>
      </div>

      <!-- Payment Entry Form -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
        <div class="p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Payment Entry</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <!-- Mode of Payment -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mode of Payment <span class="text-red-500">*</span></label>
              <select
                v-model="paymentData.mode_of_payment"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Select mode of payment</option>
                <option v-for="m in modesOfPayment" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>

            <!-- Paid Amount -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Paid Amount <span class="text-red-500">*</span></label>
              <input
                v-model.number="paymentData.paid_amount"
                type="number"
                min="0"
                step="0.01"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Reference No -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Reference No</label>
              <input
                v-model="paymentData.reference_no"
                type="text"
                placeholder="Cheque/Bank reference number"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
            </div>

            <!-- Reference Date -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Reference Date</label>
              <input
                v-model="paymentData.reference_date"
                type="date"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Payment Created Confirmation -->
      <div v-if="createdPayment" class="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
        <div class="flex items-start gap-3">
          <FeatherIcon name="check-circle" class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-green-800">Payment Entry Created: {{ createdPayment.payment_entry_id }}</p>
            <p class="text-xs text-green-700 mt-1">Paid: {{ formatCurrency(createdPayment.paid_amount) }}</p>
          </div>
        </div>
      </div>

      <!-- Payment Navigation -->
      <div class="flex justify-end items-center">
        <div class="flex items-center gap-3">
          <div v-if="paymentErrors.length > 0" class="text-red-600 text-sm flex items-center gap-2">
            <FeatherIcon name="alert-circle" class="w-4 h-4" />
            {{ paymentErrors[0] }}
          </div>
          <button
            v-if="createdPayment"
            @click="emit('continue', _buildBillingData({ ...createdInvoice, payment_entry_id: createdPayment.payment_entry_id }))"
            class="px-6 py-2 rounded-lg text-sm flex items-center gap-2 bg-genetest-navy text-white hover:opacity-90 transition-colors"
          >
            Continue to Collection
            <FeatherIcon name="arrow-right" class="w-4 h-4" />
          </button>
          <button
            v-else
            @click="submitPayment"
            :disabled="!paymentData.mode_of_payment || !paymentData.paid_amount || paymentLoading"
            :class="[
              'px-6 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors',
              paymentData.mode_of_payment && paymentData.paid_amount && !paymentLoading
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            ]"
          >
            <span v-if="paymentLoading">Submitting...</span>
            <span v-else>Submit Payment & Continue</span>
            <FeatherIcon v-if="!paymentLoading" name="check" class="w-4 h-4" />
          </button>
        </div>
      </div>
    </template>

    <!-- ═══ BILLING FORM (main view) ═══ -->
    <template v-else>

    <!-- Patient & Customer Information -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Patient & Customer Information</h3>

        <!-- Row 1: Patient ID & Patient Name (read-only) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div class="bg-gray-50 rounded-lg p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Patient ID</p>
            <p class="text-sm font-semibold text-gray-900 mt-1">{{ billingInfo.patient || props.session?.patient || 'N/A' }}</p>
          </div>
          <div class="bg-gray-50 rounded-lg p-4">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Patient Name</p>
            <p class="text-sm font-semibold text-gray-900 mt-1">{{ billingInfo.patient_name || props.session?.patient_name || 'N/A' }}</p>
          </div>
        </div>

        <!-- Row 2: Customer Group (dropdown) & Customer (searchable dropdown) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Customer Group Dropdown -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Customer Group</label>
            <select
              v-model="billingInfo.customer_group"
              @change="onCustomerGroupChange"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="">All Groups</option>
              <option v-for="g in customerGroups" :key="g" :value="g">{{ g }}</option>
            </select>
            <p class="text-xs text-gray-400 mt-1">Select a group to filter customers</p>
          </div>

          <!-- Customer Searchable Dropdown -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Customer <span class="text-red-500">*</span></label>
            <div class="relative" ref="customerDropdownRef">
              <input
                v-model="customerSearch"
                @input="searchCustomers"
                @focus="onCustomerFocus"
                type="text"
                placeholder="Search customer by name, ID, or mobile..."
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <button
                v-if="billingInfo.customer && customerSearch"
                @click="clearCustomer"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <FeatherIcon name="x" class="w-4 h-4" />
              </button>
              <div
                v-if="showCustomerDropdown && customerResults.length > 0"
                class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto"
              >
                <button
                  v-for="c in customerResults"
                  :key="c.name"
                  @click="selectCustomer(c)"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 border-b border-gray-100 last:border-0"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <span class="font-medium text-gray-900">{{ c.customer_name }}</span>
                      <span class="text-gray-400 text-xs ml-2">{{ c.name }}</span>
                    </div>
                    <span v-if="c.customer_group" class="text-xs text-gray-400">{{ c.customer_group }}</span>
                  </div>
                </button>
              </div>
            </div>
            <p v-if="billingInfo.customer" class="text-xs text-green-600 mt-1">
              Selected: {{ billingInfo.customer_name || billingInfo.customer }}
            </p>
            <p v-else class="text-xs text-amber-600 mt-1">
              No customer selected. Search and select a customer.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Include Payment Toggle -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6">
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            v-model="formData.include_payment"
            class="w-4 h-4 text-green-600 rounded focus:ring-green-500"
          />
          <div>
            <span class="text-sm font-medium text-gray-900">Include Payment</span>
            <p class="text-xs text-gray-500">Check to create a payment entry along with the sales invoice</p>
          </div>
        </label>
      </div>
    </div>

    <!-- Mark as Urgent -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6">
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            v-model="formData.mark_urgent"
            class="w-4 h-4 text-red-600 rounded focus:ring-red-500"
          />
          <div>
            <span class="text-sm font-medium text-gray-900">Mark as Urgent</span>
            <p class="text-xs text-gray-500">Lab samples will be flagged as urgent for priority processing</p>
          </div>
        </label>
      </div>
    </div>

    <!-- Payment Details (only shown when Include Payment is checked) -->
    <div v-if="formData.include_payment" class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Payment Details</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Mode of Payment <span class="text-red-500">*</span></label>
            <select
              v-model="formData.mode_of_payment"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="">Select mode of payment</option>
              <option v-for="m in modesOfPayment" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div>
            <Input
              v-model="formData.payment_reference"
              label="Reference Number"
              type="text"
              placeholder="Cheque/bank reference (optional)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Billing Details (POS, Doctor, Reference) - moved up after payment type -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Billing Details</h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <!-- POS Profile -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Shift Profile *</label>
            <select
              v-model="formData.pos_profile"
              @change="onPosProfileChange"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="">Select Shift Profile</option>
              <option v-for="p in posProfiles" :key="p.name" :value="p.name">{{ p.name }}</option>
            </select>
            <p v-if="formData.pos_profile && posProfileShiftStatus !== null" class="text-xs mt-1"
              :class="posProfileShiftStatus ? 'text-green-600' : 'text-red-600'"
            >
              {{ posProfileShiftStatus ? 'Open POS shift found' : 'No open POS shift - invoice creation will be blocked' }}
            </p>
          </div>

          <!-- Referring Doctor -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Referring Doctor <span class="text-red-600">*</span></label>
            <div class="relative flex gap-1" ref="doctorDropdownRef">
              <input
                v-model="doctorSearch"
                @input="searchDoctors"
                @focus="onDoctorFocus"
                type="text"
                placeholder="Search referring doctor..."
                class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <button
                @click="showAddPractitionerDialog = true"
                type="button"
                class="px-2.5 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-bold"
                title="Add new practitioner"
              >+</button>
              <div
                v-if="showDoctorDropdown && doctorResults.length > 0"
                class="absolute z-10 w-full mt-10 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto"
              >
                <button
                  v-for="doc in doctorResults"
                  :key="doc.name"
                  @click="selectDoctor(doc)"
                  class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                >
                  {{ doc.doctor_name }} <span class="text-gray-400 text-xs">({{ doc.specialty || doc.name }})</span>
                </button>
              </div>
            </div>
            <p v-if="formData.custom_doctor" class="text-xs text-green-600 mt-1">
              Selected: {{ formData.custom_doctor_name || formData.custom_doctor }}
            </p>
          </div>
        </div>

        <!-- External Reference -->
        <div class="mb-4">
          <Input
            v-model="formData.external_number"
            label="External Invoice / Reference Number"
            type="text"
            placeholder="Enter external reference number (optional)"
          />
        </div>

        <!-- Remarks -->
        <Input
          v-model="formData.remarks"
          type="textarea"
          label="Remarks"
          placeholder="Enter any additional billing notes or instructions..."
          :rows="3"
        />
      </div>
    </div>

    <!-- Tests to Bill -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">Tests to Bill</h3>
          <span class="text-sm text-gray-500">
            {{ selectedTests.length }} of {{ availableTests.length }} selected
          </span>
        </div>

        <!-- Search Bar -->
        <div class="mb-4">
          <div class="relative">
            <FeatherIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search tests by name, department, or sample type..."
              class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <FeatherIcon name="x" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="paginatedTests.length === 0" class="text-center py-12">
          <FeatherIcon name="inbox" class="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p class="text-gray-500 font-medium">No tests found</p>
          <p class="text-sm text-gray-400 mt-1">Try adjusting your search criteria</p>
        </div>

        <!-- Tests Table -->
        <div v-else class="border border-gray-200 rounded-lg overflow-hidden">
          <!-- Table Header -->
          <div class="bg-gray-50 px-4 py-3 border-b border-gray-200 grid grid-cols-12 gap-4 text-xs font-semibold text-gray-600 uppercase tracking-wide">
            <div class="col-span-1 flex items-center">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate="isSomeSelected"
                @change="toggleSelectAll"
                class="w-4 h-4 text-green-600 rounded focus:ring-green-500"
              />
            </div>
            <div class="col-span-3">Test Name</div>
            <div class="col-span-2">Department</div>
            <div class="col-span-1">Sample</div>
            <div class="col-span-1 text-right">Rate</div>
            <div class="col-span-1 text-center">Qty</div>
            <div class="col-span-1 text-center">Disc %</div>
            <div class="col-span-2 text-center">Disc Amount</div>
          </div>

          <!-- Table Body -->
          <div class="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            <div
              v-for="test in paginatedTests"
              :key="test.name"
              :class="[
                'px-4 py-3 grid grid-cols-12 gap-4 items-center text-sm transition-colors',
                selectedTests.includes(test.name) ? 'bg-green-50' : 'hover:bg-gray-50'
              ]"
            >
              <div class="col-span-1">
                <input
                  type="checkbox"
                  :id="test.name"
                  v-model="selectedTests"
                  :value="test.name"
                  class="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
              </div>
              <div class="col-span-3">
                <label :for="test.name" class="cursor-pointer">
                  <p class="font-medium text-gray-900">{{ test.lab_test_name }}</p>
                  <p class="text-xs text-gray-500">{{ test.lab_test_code || test.name }}</p>
                </label>
              </div>
              <div class="col-span-2">
                <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700">
                  {{ test.department || 'General' }}
                </span>
              </div>
              <div class="col-span-1">
                <span v-if="test.custom_sample_type || test.sample" class="text-gray-600 text-xs">{{ test.custom_sample_type || test.sample }}</span>
                <span v-else class="text-gray-400">&mdash;</span>
              </div>
              <div class="col-span-1 text-right">
                <!-- Rate is editable per-row once the test is selected. Blank
                     input falls back to the template rate. -->
                <input
                  v-if="selectedTests.includes(test.name)"
                  type="number"
                  min="0"
                  step="0.01"
                  :value="effectiveRate(test)"
                  @input="setRate(test, $event.target.value)"
                  :title="`Default: ${formatCurrency(test.lab_test_rate || 0)}`"
                  class="w-24 text-right border border-gray-300 rounded px-2 py-1 text-sm font-semibold text-gray-900 focus:ring-1 focus:ring-green-500"
                />
                <span v-else class="font-semibold text-gray-900">{{ formatCurrency(test.lab_test_rate) }}</span>
              </div>
              <div class="col-span-1 text-center">
                <input
                  v-if="selectedTests.includes(test.name)"
                  type="number"
                  min="1"
                  :value="(testOverrides[test.name]?.qty) || 1"
                  @input="setQty(test, $event.target.value)"
                  class="w-16 text-center border border-gray-300 rounded px-2 py-1 text-sm focus:ring-1 focus:ring-green-500"
                />
                <span v-else class="text-gray-400">&mdash;</span>
              </div>
              <div class="col-span-1 text-center">
                <input
                  v-if="selectedTests.includes(test.name)"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  :value="discountPctFor(test)"
                  @input="setDiscountPct(test, $event.target.value)"
                  class="w-16 text-center border border-gray-300 rounded px-2 py-1 text-sm focus:ring-1 focus:ring-green-500"
                />
                <span v-else class="text-gray-400">&mdash;</span>
              </div>
              <div class="col-span-2 text-center">
                <input
                  v-if="selectedTests.includes(test.name)"
                  type="number"
                  min="0"
                  step="0.01"
                  :value="discountAmountFor(test)"
                  @input="setDiscountAmount(test, $event.target.value)"
                  class="w-24 text-center border border-gray-300 rounded px-2 py-1 text-sm focus:ring-1 focus:ring-green-500"
                />
                <span v-else class="text-gray-400">&mdash;</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="mt-4 flex items-center justify-between">
          <div class="text-sm text-gray-600">
            Showing {{ startRecord }}-{{ endRecord }} of {{ filteredTests.length }} tests
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="currentPage--"
              :disabled="currentPage === 1"
              class="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FeatherIcon name="chevron-left" class="w-4 h-4" />
            </button>
            <span class="text-sm text-gray-600">Page {{ currentPage }} of {{ totalPages }}</span>
            <button
              @click="currentPage++"
              :disabled="currentPage === totalPages"
              class="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FeatherIcon name="chevron-right" class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- Total Amount -->
      <div class="p-6 bg-gray-50 border-t border-gray-200">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Total Amount</p>
            <p class="text-xs text-gray-500">{{ selectedTests.length }} test(s) selected</p>
          </div>
          <div class="text-right">
            <p class="text-2xl font-bold text-gray-900">
              {{ formatCurrency(totalAmount) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Invoice Created Confirmation -->
    <div v-if="createdInvoice" class="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
      <div class="flex items-start gap-3">
        <FeatherIcon name="check-circle" class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-medium text-green-800">Sales Invoice Created: {{ createdInvoice.invoice_id }}</p>
          <p class="text-xs text-green-700 mt-1">
            Grand Total: {{ formatCurrency(createdInvoice.grand_total) }}
            <span v-if="createdInvoice.payment_entry_id" class="ml-3">
              | Payment Entry: {{ createdInvoice.payment_entry_id }}
            </span>
            <span v-if="createdInvoice.insurance_claim_id" class="ml-3">
              | Insurance Claim: {{ createdInvoice.insurance_claim_id }}
            </span>
          </p>
          <p v-if="createdInvoice.insurance_claim_error" class="text-xs text-amber-700 mt-1">
            Insurance claim auto-creation failed: {{ createdInvoice.insurance_claim_error }}
          </p>
        </div>
      </div>
    </div>

    <!-- Navigation Buttons -->
    <div class="flex justify-end items-center">
      <div class="flex items-center gap-3">
        <div v-if="serverError || validationErrors.length > 0" class="text-red-600 text-sm flex items-center gap-2">
          <FeatherIcon name="alert-circle" class="w-4 h-4" />
          {{ serverError || validationErrors[0] }}
        </div>
        <button
          @click="handleContinueToCollection"
          :disabled="!isValid || loading"
          :class="[
            'px-5 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors border',
            isValid && !loading
              ? 'border-genetest-navy text-genetest-navy hover:bg-gray-50'
              : 'border-gray-300 text-gray-400 cursor-not-allowed'
          ]"
        >
          <span v-if="loading">Creating...</span>
          <span v-else>Continue to Collection</span>
          <FeatherIcon v-if="!loading" name="arrow-right" class="w-4 h-4" />
        </button>
        <button
          v-if="!formData.include_payment"
          @click="handleContinueToPayment"
          :disabled="!isValid || loading"
          :class="[
            'px-5 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors',
            isValid && !loading
              ? 'bg-genetest-navy text-white hover:opacity-90'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          ]"
        >
          <span v-if="loading">Creating...</span>
          <span v-else>Continue to Payment</span>
          <FeatherIcon v-if="!loading" name="dollar-sign" class="w-4 h-4" />
        </button>
      </div>
    </div>

    </template><!-- end billing form -->

    <!-- Loading Overlay -->
    <div
      v-if="loading || paymentLoading"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 flex items-center gap-3">
        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-genetest-navy"></div>
        <p class="text-sm text-gray-700">{{ paymentLoading ? 'Submitting Payment...' : 'Creating Sales Invoice...' }}</p>
      </div>
    </div>
    <!-- Add Practitioner Dialog -->
    <div v-if="showAddPractitionerDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Add New Practitioner</h3>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Full Name <span class="text-red-500">*</span></label>
          <input v-model="newPractitioner.full_name" type="text" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500" placeholder="Enter full name..." />
        </div>
        <p v-if="addPractitionerError" class="text-sm text-red-600 mt-2">{{ addPractitionerError }}</p>
        <div class="flex justify-end gap-2 mt-5">
          <button @click="closeAddPractitionerDialog" type="button" class="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200">Cancel</button>
          <button @click="saveNewPractitioner" :disabled="addingPractitioner" type="button" class="px-4 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50">
            {{ addingPractitioner ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { call, frappeError } from '@/api/client'
import FeatherIcon from '@/components/ui/FeatherIcon.vue'
import FInput from '@/components/ui/FInput.vue'
import SectionHeader from '@/components/ui/SectionHeader.vue'

const props = defineProps({
  session: {
    type: Object,
    required: true
  },
  billingData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['continue'])

// Form data
const formData = ref({
  include_payment: false,
  payment_type: '',
  mode_of_payment: '',
  payment_reference: '',
  insurance_provider: '',
  insurance_provider_name: '',
  policy_number: '',
  member_id: '',
  authorization_number: '',
  corporate_account: '',
  corporate_account_name: '',
  external_number: '',
  remarks: '',
  custom_doctor: '',
  custom_doctor_name: '',
  pos_profile: '',
  mark_urgent: false
})

// Billing info from patient
const billingInfo = ref({
  patient: '',
  patient_name: '',
  customer: '',
  customer_name: '',
  customer_group: ''
})

// Customer groups
const customerGroups = ref([])

// Customer search state
const customerSearch = ref('')
const customerResults = ref([])
const showCustomerDropdown = ref(false)
const customerDropdownRef = ref(null)

// Available tests
const availableTests = ref([])
const selectedTests = ref([])

// Search and pagination
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = 10

// Loading state
const loading = ref(false)

// Created invoice tracking (to prevent double-creation)
const createdInvoice = ref(null)

// Insurance provider search state
const insuranceProviderSearch = ref('')
const insuranceProviderResults = ref([])
const showInsuranceDropdown = ref(false)

// Corporate account search state
const corporateAccountSearch = ref('')
const corporateAccountResults = ref([])
const showCorporateDropdown = ref(false)

// POS state
const posProfiles = ref([])
const posProfileShiftStatus = ref(null)

// Server-side error (distinct from `validationErrors`, which is a computed
// derived from form state — assigning to a computed is silently dropped, so
// API errors were never displayed before this ref existed).
const serverError = ref('')

// Referring doctor search state
const doctorSearch = ref('')
const doctorResults = ref([])
const showDoctorDropdown = ref(false)
const doctorDropdownRef = ref(null)

// Add Practitioner dialog state
const showAddPractitionerDialog = ref(false)
const addingPractitioner = ref(false)
const addPractitionerError = ref('')
const newPractitioner = ref({ full_name: '' })
const insuranceDropdownRef = ref(null)
const corporateDropdownRef = ref(null)

// Payment form state
const showPaymentForm = ref(false)
const paymentData = ref({ mode_of_payment: '', paid_amount: 0, reference_no: '', reference_date: '' })
const modesOfPayment = ref([])
const createdPayment = ref(null)
const paymentLoading = ref(false)
const paymentErrors = ref([])

// Per-test overrides — { [testName]: { qty, discount_percentage, rate } }.
// Discount percentage is the SOURCE OF TRUTH (that's what the backend
// invoice uses); the discount-amount column is just a two-way derived view.
// `rate` is optional — when set, it overrides the Lab Test Template's
// `lab_test_rate` for this invoice line. Decimal values supported.
const testOverrides = ref({})

// The effective rate for a test row — override if the user typed one,
// otherwise fall back to the Lab Test Template's configured rate. Used by
// every downstream calc (line total, discount cap, grand total).
function effectiveRate(test) {
  const ov = testOverrides.value[test.name]
  if (ov && typeof ov.rate === 'number' && !Number.isNaN(ov.rate)) {
    return ov.rate
  }
  return test.lab_test_rate || 0
}

function setQty(test, raw) {
  const qty = Math.max(1, parseInt(raw, 10) || 1)
  testOverrides.value[test.name] = { ...(testOverrides.value[test.name] || {}), qty }
}
function setRate(test, raw) {
  const rate = Math.max(0, parseFloat(raw) || 0)
  testOverrides.value[test.name] = { ...(testOverrides.value[test.name] || { qty: 1 }), rate }
}
// Discount % / Discount Amount — both go through to the backend as-is, the
// way ERPNext's Sales Invoice natively supports (either field is a valid
// input; ERPNext derives the other). We store whichever the user last
// touched and clear its counterpart so the payload carries the user's
// actual intent, not a round-tripped derivation that can silently zero out.
function setDiscountPct(test, raw) {
  const pct = Math.max(0, Math.min(100, parseFloat(raw) || 0))
  const ov = testOverrides.value[test.name] || { qty: 1 }
  const next = { ...ov, discount_percentage: pct }
  delete next.discount_amount
  testOverrides.value[test.name] = next
}
function setDiscountAmount(test, raw) {
  const amt = Math.max(0, parseFloat(raw) || 0)
  const ov = testOverrides.value[test.name] || { qty: 1 }
  const next = { ...ov, discount_amount: amt }
  delete next.discount_percentage
  testOverrides.value[test.name] = next
}
// Live discount amount for the Discount Amount input's :value. If the user
// entered a percentage, derive amount from qty × rate × pct for display.
// If they entered an amount directly, show that.
function discountAmountFor(test) {
  const ov = testOverrides.value[test.name]
  if (!ov) return 0
  if (typeof ov.discount_amount === 'number') return ov.discount_amount
  const base = (ov.qty || 1) * effectiveRate(test)
  return +(base * ((ov.discount_percentage || 0) / 100)).toFixed(2)
}
// Live discount percentage for the Discount % input's :value. Mirror of
// discountAmountFor for the opposite field.
function discountPctFor(test) {
  const ov = testOverrides.value[test.name]
  if (!ov) return 0
  if (typeof ov.discount_percentage === 'number') return ov.discount_percentage
  const base = (ov.qty || 1) * effectiveRate(test)
  if (base <= 0) return 0
  return +(((ov.discount_amount || 0) / base) * 100).toFixed(4)
}

// Payment type options
const paymentTypeOptions = [
  { value: 'Cash', label: 'Cash Payment', description: 'Patient pays directly', icon: 'dollar-sign' },
  { value: 'Insurance', label: 'Insurance', description: 'Billed to insurance company', icon: 'shield' },
  { value: 'Corporate', label: 'Corporate', description: 'Billed to corporate account', icon: 'briefcase' }
]

// ── Customer Group & Customer logic ──

const loadCustomerGroups = async () => {
  try {
    const groups = await call('diagnostic_management.api.billing_workflow.get_customer_groups')
    customerGroups.value = groups || []
  } catch (e) {
    console.error('Failed to load customer groups:', e)
  }
}

let customerSearchTimeout = null
const searchCustomers = () => {
  clearTimeout(customerSearchTimeout)
  customerSearchTimeout = setTimeout(async () => {
    try {
      const params = { search_term: customerSearch.value || '', limit: 15 }
      if (billingInfo.value.customer_group) {
        params.customer_group = billingInfo.value.customer_group
      }
      const results = await call('diagnostic_management.api.billing_workflow.search_customers', params)
      customerResults.value = results || []
      showCustomerDropdown.value = true
    } catch (e) {
      console.error('Customer search failed:', e)
      customerResults.value = []
    }
  }, 300)
}

const onCustomerFocus = () => {
  // Show recent customers on focus (even without typing)
  if (customerResults.value.length === 0) {
    searchCustomers()
  } else {
    showCustomerDropdown.value = true
  }
}

const selectCustomer = (c) => {
  billingInfo.value.customer = c.name
  billingInfo.value.customer_name = c.customer_name
  customerSearch.value = c.customer_name
  showCustomerDropdown.value = false

  // Auto-populate customer group from selected customer
  if (c.customer_group) {
    billingInfo.value.customer_group = c.customer_group
  }
}

const clearCustomer = () => {
  billingInfo.value.customer = ''
  billingInfo.value.customer_name = ''
  customerSearch.value = ''
  customerResults.value = []
}

const onCustomerGroupChange = () => {
  // When customer group changes, clear current customer and re-search
  billingInfo.value.customer = ''
  billingInfo.value.customer_name = ''
  customerSearch.value = ''
  customerResults.value = []
  // Trigger a fresh search with the new group filter
  searchCustomers()
}

// Filtered tests based on search
const filteredTests = computed(() => {
  if (!searchQuery.value) return availableTests.value
  const query = searchQuery.value.toLowerCase()
  return availableTests.value.filter(test =>
    test.lab_test_name?.toLowerCase().includes(query) ||
    test.lab_test_code?.toLowerCase().includes(query) ||
    test.department?.toLowerCase().includes(query) ||
    (test.custom_sample_type || test.sample)?.toLowerCase().includes(query)
  )
})

// Pagination
const totalPages = computed(() => Math.ceil(filteredTests.value.length / pageSize))
const paginatedTests = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredTests.value.slice(start, start + pageSize)
})
const startRecord = computed(() => filteredTests.value.length === 0 ? 0 : (currentPage.value - 1) * pageSize + 1)
const endRecord = computed(() => Math.min(currentPage.value * pageSize, filteredTests.value.length))

// Select all
const isAllSelected = computed(() =>
  filteredTests.value.length > 0 && filteredTests.value.every(t => selectedTests.value.includes(t.name))
)
const isSomeSelected = computed(() =>
  filteredTests.value.some(t => selectedTests.value.includes(t.name)) && !isAllSelected.value
)
const toggleSelectAll = () => {
  const names = filteredTests.value.map(t => t.name)
  if (isAllSelected.value) {
    selectedTests.value = selectedTests.value.filter(n => !names.includes(n))
  } else {
    selectedTests.value = [...selectedTests.value, ...names.filter(n => !selectedTests.value.includes(n))]
  }
}

watch(searchQuery, () => { currentPage.value = 1 })

// Validation (separate computed properties to avoid reactive side-effects)
const validationErrors = computed(() => {
  const errors = []
  if (!billingInfo.value.customer) errors.push('Customer required')
  if (formData.value.include_payment) {
    if (!formData.value.mode_of_payment) errors.push('Mode of payment required')
  }
  if (selectedTests.value.length === 0) errors.push('Select at least one test')
  return errors
})
const isValid = computed(() => validationErrors.value.length === 0)

// Total amount
const totalAmount = computed(() =>
  selectedTests.value.reduce((total, testName) => {
    const test = availableTests.value.find(t => t.name === testName)
    if (!test) return total
    const ov = testOverrides.value[testName] || {}
    // Mirror effectiveRate() — override wins over the template's rate.
    const rate = (typeof ov.rate === 'number' && !Number.isNaN(ov.rate))
      ? ov.rate
      : (test.lab_test_rate || 0)
    const gross = (ov.qty || 1) * rate
    // Discount can be entered as either % or amount (mirrors ERPNext). The
    // two setters clear their counterpart, so at most one is set here.
    let discount = 0
    if (typeof ov.discount_amount === 'number') discount = Math.min(gross, ov.discount_amount)
    else if (typeof ov.discount_percentage === 'number') discount = gross * (ov.discount_percentage / 100)
    return total + Math.max(0, gross - discount)
  }, 0)
)

// ── Search helpers ──

let insuranceSearchTimeout = null
const searchInsuranceProviders = () => {
  clearTimeout(insuranceSearchTimeout)
  insuranceSearchTimeout = setTimeout(async () => {
    if (!insuranceProviderSearch.value || insuranceProviderSearch.value.length < 1) {
      insuranceProviderResults.value = []; return
    }
    try {
      const results = await call('diagnostic_management.api.billing_workflow.search_insurance_providers', { search_term: insuranceProviderSearch.value })
      insuranceProviderResults.value = results || []
      showInsuranceDropdown.value = true
    } catch (e) { insuranceProviderResults.value = [] }
  }, 300)
}
const selectInsuranceProvider = (provider) => {
  formData.value.insurance_provider = provider.name
  formData.value.insurance_provider_name = provider.customer_name
  insuranceProviderSearch.value = provider.customer_name
  showInsuranceDropdown.value = false
}

let corporateSearchTimeout = null
const searchCorporateAccounts = () => {
  clearTimeout(corporateSearchTimeout)
  corporateSearchTimeout = setTimeout(async () => {
    if (!corporateAccountSearch.value || corporateAccountSearch.value.length < 1) {
      corporateAccountResults.value = []; return
    }
    try {
      const results = await call('diagnostic_management.api.billing_workflow.search_corporate_accounts', { search_term: corporateAccountSearch.value })
      corporateAccountResults.value = results || []
      showCorporateDropdown.value = true
    } catch (e) { corporateAccountResults.value = [] }
  }, 300)
}
const selectCorporateAccount = (account) => {
  formData.value.corporate_account = account.name
  formData.value.corporate_account_name = account.customer_name
  corporateAccountSearch.value = account.customer_name
  showCorporateDropdown.value = false
}

// Close dropdowns on outside click
const handleClickOutside = (e) => {
  if (customerDropdownRef.value && !customerDropdownRef.value.contains(e.target)) {
    showCustomerDropdown.value = false
  }
  if (insuranceDropdownRef.value && !insuranceDropdownRef.value.contains(e.target)) {
    showInsuranceDropdown.value = false
  }
  if (corporateDropdownRef.value && !corporateDropdownRef.value.contains(e.target)) {
    showCorporateDropdown.value = false
  }
  if (doctorDropdownRef.value && !doctorDropdownRef.value.contains(e.target)) {
    showDoctorDropdown.value = false
  }
}

// ── POS helpers ──
const loadPosProfiles = async () => {
  try {
    const profiles = await call('diagnostic_management.api.billing_workflow.get_user_pos_profiles')
    posProfiles.value = profiles || []
    // Drop a stale selection (e.g. a rehydrated value from props.billingData
    // pointing at a profile that was deleted/renamed) before the form would
    // submit it and trip a LinkValidationError on the server.
    const validNames = new Set(posProfiles.value.map(p => p.name))
    if (formData.value.pos_profile && !validNames.has(formData.value.pos_profile)) {
      formData.value.pos_profile = ''
    }
    // Auto-select if user has exactly one profile, or select first available
    if (!formData.value.pos_profile && posProfiles.value.length > 0) {
      formData.value.pos_profile = posProfiles.value[0].name
      await onPosProfileChange()
    }
  } catch (e) { console.error('POS profiles load failed:', e) }
}
const onPosProfileChange = async () => {
  if (!formData.value.pos_profile) { posProfileShiftStatus.value = null; return }
  try {
    const result = await call('diagnostic_management.api.billing_workflow.check_pos_profile_shift', { pos_profile: formData.value.pos_profile })
    posProfileShiftStatus.value = result?.has_open_shift || false
  } catch (e) { posProfileShiftStatus.value = false }
}

// ── Doctor search (Healthcare Practitioner) ──
let doctorSearchTimeout = null
const searchDoctors = () => {
  clearTimeout(doctorSearchTimeout)
  doctorSearchTimeout = setTimeout(async () => {
    try {
      const results = await call('diagnostic_management.api.billing_workflow.search_doctors', {
        search_term: doctorSearch.value || '',
        limit: 10
      })
      doctorResults.value = results || []
      showDoctorDropdown.value = true
    } catch (e) {
      console.error('Practitioner search failed:', e)
      doctorResults.value = []
    }
  }, 300)
}
const onDoctorFocus = () => {
  if (doctorResults.value.length === 0) {
    searchDoctors()
  } else {
    showDoctorDropdown.value = true
  }
}
const selectDoctor = (doc) => {
  formData.value.custom_doctor = doc.name
  formData.value.custom_doctor_name = doc.doctor_name
  doctorSearch.value = doc.doctor_name
  showDoctorDropdown.value = false
}

const closeAddPractitionerDialog = () => {
  showAddPractitionerDialog.value = false
  addPractitionerError.value = ''
  newPractitioner.value = { full_name: '' }
}

const saveNewPractitioner = async () => {
  const fullName = newPractitioner.value.full_name?.trim()
  if (!fullName) {
    addPractitionerError.value = 'Full name is required'
    return
  }
  addingPractitioner.value = true
  addPractitionerError.value = ''
  try {
    const result = await call('diagnostic_management.api.billing_workflow.create_doctor', {
      doctor_name: fullName
    })
    formData.value.custom_doctor = result.name
    formData.value.custom_doctor_name = result.doctor_name
    doctorSearch.value = result.doctor_name
    closeAddPractitionerDialog()
  } catch (e) {
    addPractitionerError.value = e.messages?.[0] || 'Failed to create doctor'
  } finally {
    addingPractitioner.value = false
  }
}

// ── Load billing info ──
const loadBillingInfo = async () => {
  if (!props.session?.patient) {
    loadAvailableTests()
    return
  }
  try {
    loading.value = true
    const info = await call('diagnostic_management.api.billing_workflow.get_patient_billing_info', { patient_id: props.session.patient })
    billingInfo.value = info || { patient: '', patient_name: '', customer: '', customer_name: '', customer_group: '', patient_gender: '' }
    // Pre-fill the customer search input
    if (billingInfo.value.customer_name) {
      customerSearch.value = billingInfo.value.customer_name
    }
  } catch (e) {
    console.error('Failed to load billing info:', e)
  } finally {
    loading.value = false
    // Always load tests after billing info (with or without gender)
    loadAvailableTests()
  }
}

// Load available tests (filtered by patient gender)
const loadAvailableTests = async () => {
  try {
    loading.value = true
    const tests = await call('diagnostic_management.api.billing_workflow.get_lab_tests_for_billing', {
      tests: null,
      patient_gender: billingInfo.value.patient_gender || null
    })
    availableTests.value = tests || []
    if (props.billingData?.selected_tests) {
      selectedTests.value = props.billingData.selected_tests
    }
  } catch (e) {
    console.error('Failed to load tests:', e)
    availableTests.value = []
  } finally {
    loading.value = false
  }
}

const formatCurrency = (amount) => {
  if (!amount && amount !== 0) return 'KES 0.00'
  return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES', minimumFractionDigits: 2 }).format(amount || 0)
}

// Create the invoice (shared logic for both buttons)
const _createInvoice = async () => {
  if (createdInvoice.value) return createdInvoice.value

  // Mandatory: a Referring Doctor must be picked or typed before the order
  // can be billed. The selection writes into `formData.custom_doctor`.
  if (!formData.value.custom_doctor) {
    // Surface inline; matches how other validation errors are reported.
    if (typeof error !== 'undefined' && error && 'value' in error) {
      // eslint-disable-next-line vue/no-mutating-props
      error.value = 'Referring Doctor is required.'
    } else {
      alert('Referring Doctor is required.')
    }
    throw new Error('referring_doctor_required')
  }

  const billingPayload = {
    customer: billingInfo.value.customer,
    include_payment: formData.value.include_payment,
    payment_type: formData.value.include_payment ? 'Cash' : '',
    mode_of_payment: formData.value.include_payment ? formData.value.mode_of_payment : '',
    payment_reference: formData.value.include_payment ? formData.value.payment_reference : '',
    selected_tests: selectedTests.value.map(testName => {
      const ov = testOverrides.value[testName]
      const hasRateOverride = ov && typeof ov.rate === 'number' && !Number.isNaN(ov.rate)
      const hasPct = ov && typeof ov.discount_percentage === 'number' && ov.discount_percentage > 0
      const hasAmt = ov && typeof ov.discount_amount === 'number' && ov.discount_amount > 0
      if (ov && (ov.qty !== 1 || hasPct || hasAmt || hasRateOverride)) {
        const row = { lab_test_template: testName, qty: ov.qty || 1 }
        // Send whichever the user actually typed — ERPNext's Sales Invoice
        // accepts either field on the item line and derives the other.
        if (hasPct) row.discount_percentage = ov.discount_percentage
        if (hasAmt) row.discount_amount = ov.discount_amount
        if (hasRateOverride) row.rate = ov.rate
        return row
      }
      return testName
    }),
    remarks: formData.value.remarks,
    external_number: formData.value.external_number || null,
    custom_doctor: formData.value.custom_doctor || null,
    pos_profile: formData.value.pos_profile || null,
    mark_urgent: formData.value.mark_urgent
  }

  const result = await call('diagnostic_management.api.billing_workflow.create_sales_invoice_for_tests', {
    session_id: props.session.name,
    billing_data: billingPayload
  })

  if (result && result.success) {
    createdInvoice.value = result
    return result
  }
  throw new Error('Failed to create Sales Invoice')
}

// Continue to Collection: create invoice → go to next step
const handleContinueToCollection = async () => {
  serverError.value = ''
  if (!isValid.value) { serverError.value = validationErrors.value[0]; return }
  if (createdInvoice.value) { emit('continue', _buildBillingData()); return }

  try {
    loading.value = true
    const result = await _createInvoice()
    emit('continue', _buildBillingData(result))
  } catch (error) {
    console.error('Failed to create invoice:', error)
    serverError.value = frappeError(error, 'Failed to create Sales Invoice')
  } finally {
    loading.value = false
  }
}

// Continue to Payment: create invoice → check outstanding → show payment form
const handleContinueToPayment = async () => {
  serverError.value = ''
  if (!isValid.value) { serverError.value = validationErrors.value[0]; return }

  try {
    loading.value = true
    const result = await _createInvoice()

    // Check the invoice's actual outstanding amount from the server
    const invoiceStatus = await call('diagnostic_management.api.billing_workflow.get_invoice_outstanding', {
      invoice_id: result.invoice_id
    })

    if (invoiceStatus && invoiceStatus.outstanding_amount <= 0) {
      // Invoice is already fully paid (e.g. from POS auto-payment) — skip payment form
      createdPayment.value = {
        payment_entry_id: 'Auto-paid (POS)',
        paid_amount: invoiceStatus.grand_total || result.grand_total
      }
      showPaymentForm.value = true
      return
    }

    // Pre-fill payment amount with outstanding amount
    paymentData.value.paid_amount = invoiceStatus?.outstanding_amount || result.grand_total || totalAmount.value
    showPaymentForm.value = true
  } catch (error) {
    console.error('Failed to create invoice:', error)
    serverError.value = frappeError(error, 'Failed to create Sales Invoice')
  } finally {
    loading.value = false
  }
}

// Submit payment entry
const submitPayment = async () => {
  paymentErrors.value = []
  if (!paymentData.value.mode_of_payment) { paymentErrors.value = ['Mode of payment required']; return }
  if (!paymentData.value.paid_amount || paymentData.value.paid_amount <= 0) { paymentErrors.value = ['Paid amount must be greater than 0']; return }

  try {
    paymentLoading.value = true
    const result = await call('diagnostic_management.api.billing_workflow.create_payment_entry_for_invoice', {
      invoice_id: createdInvoice.value.invoice_id,
      mode_of_payment: paymentData.value.mode_of_payment,
      paid_amount: paymentData.value.paid_amount,
      reference_no: paymentData.value.reference_no || '',
      reference_date: paymentData.value.reference_date || ''
    })

    if (result && result.success) {
      if (result.already_paid) {
        // Invoice was already paid — show as success so user can proceed
        createdPayment.value = {
          payment_entry_id: 'Already paid',
          paid_amount: result.paid_amount || 0
        }
      } else {
        createdPayment.value = result
      }
    } else {
      paymentErrors.value = ['Failed to create Payment Entry']
    }
  } catch (error) {
    console.error('Failed to create payment:', error)
    let msg = 'Failed to create Payment Entry'
    if (error.messages && error.messages.length) {
      msg = error.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
    } else if (error.message) { msg = error.message }
    paymentErrors.value = [msg]
  } finally {
    paymentLoading.value = false
  }
}

// Load modes of payment
const loadModesOfPayment = async () => {
  try {
    const modes = await call('diagnostic_management.api.billing_workflow.get_modes_of_payment')
    modesOfPayment.value = modes || []
  } catch (e) { console.error('Failed to load modes of payment:', e) }
}

const _buildBillingData = (invoiceResult = null) => ({
  customer: billingInfo.value.customer,
  customer_name: billingInfo.value.customer_name,
  include_payment: formData.value.include_payment,
  payment_type: formData.value.include_payment ? 'Cash' : '',
  mode_of_payment: formData.value.include_payment ? formData.value.mode_of_payment : '',
  payment_reference: formData.value.include_payment ? formData.value.payment_reference : '',
  mark_urgent: formData.value.mark_urgent,
  selected_tests: selectedTests.value,
  total_amount: totalAmount.value,
  external_number: formData.value.external_number,
  remarks: formData.value.remarks,
  invoice_id: invoiceResult?.invoice_id || createdInvoice.value?.invoice_id,
  payment_entry_id: invoiceResult?.payment_entry_id || createdInvoice.value?.payment_entry_id,
  insurance_claim_id: invoiceResult?.insurance_claim_id || createdInvoice.value?.insurance_claim_id,
  items: selectedTests.value.map(testName => {
    const test = availableTests.value.find(t => t.name === testName)
    const ov = testOverrides.value[testName] || {}
    return {
      item_code: testName,
      item_name: test?.lab_test_name,
      qty: ov.qty || 1,
      discount_percentage: ov.discount_percentage || 0,
      rate: test?.lab_test_rate || 0,
      amount: (ov.qty || 1) * (test?.lab_test_rate || 0) * (1 - (ov.discount_percentage || 0) / 100),
      sample: test?.custom_sample_type || test?.sample,
      sample_uom: test?.sample_uom,
      sample_details: test?.sample_details,
      department: test?.department
    }
  })
})

// Watch session
watch(() => props.session?.patient, (newPatient) => {
  if (newPatient) loadBillingInfo()
}, { immediate: true })

watch(() => props.session?.sales_invoice, (invoiceId) => {
  if (invoiceId) createdInvoice.value = { invoice_id: invoiceId, success: true }
}, { immediate: true })

onMounted(() => {
  loadBillingInfo()
  loadPosProfiles()
  loadCustomerGroups()
  loadModesOfPayment()

  document.addEventListener('click', handleClickOutside)

  if (props.billingData) {
    formData.value.include_payment = props.billingData.include_payment || false
    formData.value.payment_type = props.billingData.payment_type || ''
    formData.value.insurance_provider = props.billingData.insurance_provider || ''
    formData.value.insurance_provider_name = props.billingData.insurance_provider_name || ''
    formData.value.policy_number = props.billingData.policy_number || ''
    formData.value.member_id = props.billingData.member_id || ''
    formData.value.authorization_number = props.billingData.authorization_number || ''
    formData.value.corporate_account = props.billingData.corporate_account || ''
    formData.value.corporate_account_name = props.billingData.corporate_account_name || ''
    formData.value.external_number = props.billingData.external_number || ''
    formData.value.remarks = props.billingData.remarks || ''
    if (props.billingData.insurance_provider_name) insuranceProviderSearch.value = props.billingData.insurance_provider_name
    if (props.billingData.corporate_account_name) corporateAccountSearch.value = props.billingData.corporate_account_name
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.step-content {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.divide-y > div {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}
.divide-y > div::-webkit-scrollbar { width: 6px; }
.divide-y > div::-webkit-scrollbar-track { background: transparent; }
.divide-y > div::-webkit-scrollbar-thumb { background-color: #d1d5db; border-radius: 3px; }
.divide-y > div::-webkit-scrollbar-thumb:hover { background-color: #9ca3af; }
</style>
