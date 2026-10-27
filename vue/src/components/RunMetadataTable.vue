<template>
  <div class="run-metadata-table">
    <!-- No mobile cards: the columns have no labels, so Buefy's phone card
         layout (label left, value right) pushed every cell to the right edge.
         The phone styles below lay it out as a narrow normal table instead. -->
    <p v-if="sources.length" class="source-key">
      <span v-for="s in sources" :key="s.key" :class="['source-chip', 'src-' + s.key]">{{ s.label }}</span>
    </p>
    <slot name="after-key" />
    <b-table :data="shown_rows" :striped="true" detailed :show-detail-icon="false" :mobile-cards="false" :row-class="row => row.source ? 'src-' + row.source : ''">
      <b-table-column field="is_custom" label="" align="center" v-slot="props" width="20">
        <button v-if="!props.row.is_custom" type="button" class="metadata-detail-toggle" :aria-label="`Show details for ${props.row.k}`" @click="props.toggleDetails(props.row)">
          <b-icon icon="information-outline" />
        </button>
      </b-table-column>

      <b-table-column field="k" label="" v-slot="props" width="300">
        <div :class="['metadata-key-cell', { 'is-unique': props.row.unique }]" :title="props.row.unique ? UNIQUE_LABEL : null">
          <button type="button" class="metadata-key-toggle" @click="props.toggleDetails(props.row)">
            <b>{{ props.row.k }}</b>
          </button>
        </div>
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

      <template v-if="empty_text" #empty>
        <p class="empty-note">{{ empty_text }}</p>
      </template>

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
const UNIQUE_LABEL = 'Unique to this sample compared against the BioProject'
const SOURCE_LABELS = { metalog: 'Metalog' }

export default {
  name: 'RunMetadataTable',
  props: ['table_data', 'empty_text'],
  computed: {
    shown_rows () {
      return this.table_data || []
    },
    // Sources that rows in this table are tagged with (none for most tables).
    sources () {
      const keys = [...new Set((this.table_data || []).map(r => r.source).filter(Boolean))]
      return keys.map(key => ({ key, label: SOURCE_LABELS[key] }))
    }
  },
  data() {
    return {
      UNIQUE_LABEL,
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
.source-key {
  margin-bottom: 0.5rem;
}
.source-chip {
  display: inline-block;
  margin-right: 0.4rem;
  padding: 0.1rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
}
.source-chip.src-metalog, .run-metadata-table :deep(tr.src-metalog > td) { background: #dbe9f6; }
.empty-note {
  padding: 0.75rem 1rem;
  color: #888;
  font-style: italic;
  text-align: left;
}
.metadata-key-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.metadata-key-cell.is-unique {
  border-left: 3px solid hsl(174, 62%, 28%);
  padding-left: 0.3rem;
}
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
  /* Only real rows: the description that opens under a row ("i") is a
     separate tr.detail whose text sits in its first cell, and squeezing that
     to the icon column's 2.75rem put every word on its own line. */
  /* !important: the columns' width="20"/width="300" props become inline
     styles, which otherwise win here and left the value column ~36px wide on
     a phone (one or two letters per line). First column fits the 44px "i"
     tap target plus its cell padding, so the name cell no longer covers it. */
  .run-metadata-table :deep(th:first-child),
  .run-metadata-table :deep(tr:not(.detail) > td:first-child) {
    width: calc(44px + 0.7rem) !important;
  }
  .run-metadata-table :deep(th:nth-child(2)),
  .run-metadata-table :deep(tr:not(.detail) > td:nth-child(2)) {
    width: 38% !important;
  }
  .run-metadata-table :deep(th:nth-child(3)),
  .run-metadata-table :deep(tr:not(.detail) > td:nth-child(3)) {
    width: auto !important;
  }
  .run-metadata-table :deep(tr.detail > td) {
    width: auto;
  }
}
</style>
