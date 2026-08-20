<template>
  <div class="run-metadata-table">
    <b-table :data="table_data" :striped="true" detailed :show-detail-icon="false">
      <b-table-column field="is_custom" label="" align="center" v-slot="props" width="20">
        <button v-if="!props.row.is_custom" type="button" class="metadata-detail-toggle" :aria-label="`Show details for ${props.row.k}`" @click="props.toggleDetails(props.row)">
          <b-icon icon="information-outline" />
        </button>
      </b-table-column>

      <b-table-column field="k" label="" v-slot="props" width="300">
        <button type="button" class="metadata-key-toggle" @click="props.toggleDetails(props.row)">
          <b>{{ props.row.k }}</b>
        </button>
      </b-table-column>

      <b-table-column field="v" label="" v-slot="props">
        <div v-if="props.row.k.toLowerCase().includes('email')">
          <span v-if="verifiedEmails.includes(props.row.k)">
            {{ props.row.v }}
          </span>
          <span v-else-if="activeRecaptcha === props.row.k">
            <div :id="'recaptcha-container-' + props.row.k"></div>
          </span>
          <button v-else type="button" class="email-hidden" @click="showRecaptcha(props.row.k)">
            (hidden, click to reveal)
          </button>
        </div>
        <div v-else>
          {{ props.row.v }}
        </div>
      </b-table-column>

      <template #detail="props">
        <div v-if="props.row.is_custom">
          "{{props.row.k}}" is a custom attribute that is not defined by NCBI.
        </div>
        <div v-else>
          "{{props.row.k}}" is {{props.row.description}}
        </div>
      </template>
    </b-table>
  </div>
</template>

<script>
import { verifyRecaptcha } from '@/api'
export default {
  name: 'RunMetadataTable',
  props: ['table_data'],
  data() {
    return {
      recaptchaSiteKey: '6LdZXhorAAAAAMxLgnqZRC7KQrTE-l1Sa4KLunJQ', // your reCAPTCHA site key
      verifiedEmails: [],                     // tracks verified email keys
      activeRecaptcha: null,                  // tracks the currently displayed reCAPTCHA
    };
  },
  methods: {
    verifyCallback(k, token) {
      // Immediately send token to backend
      verifyRecaptcha(token)
        .then(res => {
          if (res.data.success) {
            this.verifiedEmails.push(k);
          } else {
            alert('Verification failed. Try again.');
          }
          this.activeRecaptcha = null;
        })
        .catch(err => {
          console.error(err);
          alert('Verification error.');
          this.activeRecaptcha = null;
        });
    },
    showRecaptcha(k) {
      this.activeRecaptcha = k;
      this.$nextTick(() => {
        grecaptcha.render(`recaptcha-container-${k}`, {
          sitekey: this.recaptchaSiteKey,
          size: window.innerWidth <= 430 ? 'compact' : 'normal',
          callback: (token) => this.verifyCallback(k, token),
          'expired-callback': () => (this.activeRecaptcha = null),
        });
      });
    },
  },
};
</script>

<style scoped>
.email-hidden {
  appearance: none;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  color: #007bff;
  text-decoration: underline;
}
.email-hidden:hover {
  color: #0056b3;
}
.metadata-detail-toggle,
.metadata-key-toggle {
  appearance: none;
  border: 0;
  padding: 0.2rem;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
}
.metadata-detail-toggle:focus-visible,
.metadata-key-toggle:focus-visible,
.email-hidden:focus-visible {
  outline: 2px solid #3273dc;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .metadata-detail-toggle {
    min-width: 44px;
    min-height: 44px;
  }
  .metadata-key-toggle,
  .email-hidden {
    min-height: 44px;
  }
  .run-metadata-table {
    max-width: 100%;
  }
  .run-metadata-table :deep(.table-wrapper) {
    max-width: 100%;
    overflow-x: auto;
  }
  .run-metadata-table :deep(table) {
    table-layout: fixed;
    width: 100%;
  }
  .run-metadata-table :deep(th),
  .run-metadata-table :deep(td) {
    height: auto;
    padding: 0.55rem 0.35rem;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
  .run-metadata-table :deep(th:first-child),
  .run-metadata-table :deep(td:first-child) {
    width: 2.75rem;
  }
  .run-metadata-table :deep(th:nth-child(2)),
  .run-metadata-table :deep(td:nth-child(2)) {
    width: 38%;
  }
}
</style>
