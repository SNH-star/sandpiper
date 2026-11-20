// What the group density figures (known species fraction, prokaryotic fraction, genome size by host or environment)
// plot. Shared by the charts and by their CSV tables.

import { HOST_GROUPS, ECOLOGICAL_GROUPS } from './groupColours'

// What each measure plots; `prefix` picks its histograms out of the version summary.
export const MEASURES = {
  known: {
    prefix: '',
    idSuffix: '',
    title: 'Known species fraction',
    note: 'The share of a run’s community that belongs to species already named in GTDB.',
    x_title: 'Known species fraction (%)',
    describe: 'Known species fraction',
    unit: '%',
    x_step: 1,
    x_ticks: [0, 25, 50, 75, 100]
  },
  spf: {
    prefix: 'spf_',
    idSuffix: '-spf',
    title: 'Prokaryotic fraction',
    note: 'The share of a run’s reads that SingleM estimates are bacterial or archaeal (SPF).',
    x_title: 'Prokaryotic fraction (%)',
    describe: 'Prokaryotic fraction (SPF)',
    unit: '%',
    x_step: 1,
    x_ticks: [0, 25, 50, 75, 100]
  },
  genome: {
    prefix: 'genome_size_',
    idSuffix: '-genome',
    title: 'Average genome size',
    note: 'The average genome size of the bacteria and archaea in each run. Runs above 8 Mb are counted in the last bin.',
    x_title: 'Genome size (Mb)',
    describe: 'Average genome size',
    unit: ' Mb',
    x_step: 0.25,
    x_ticks: [0, 2, 4, 6, 8]
  }
}

export const FIGURES = {
  host: {
    id: 'host-groups',
    title: 'Eukaryotic host-associated samples',
    note: 'Known species fraction in host-associated runs, by host.',
    key: 'host_groups',
    gutNote: ' (for bovine, human, mouse and pig also “<name> gut metagenome”)',
    groups: HOST_GROUPS.map(({ key, label, colour }) => ({ name: key, label, colour }))
  },
  ecological: {
    id: 'ecological-groups',
    title: 'Ecological samples',
    note: 'Known species fraction in ecological runs, by environment.',
    key: 'ecological_groups',
    gutNote: '',
    groups: ECOLOGICAL_GROUPS.map(({ key, label, colour }) => ({ name: key, label, colour }))
  }
}
