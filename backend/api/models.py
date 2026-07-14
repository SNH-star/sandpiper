"""
models.py
- Data classes for SingleM databases
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

class Marker(db.Model):
    __tablename__ = 'markers'
    id = db.Column(db.Integer, server_default=text("nextval('markers_id_seq')"), primary_key=True)
    marker = db.Column(db.String, nullable=False)

    def to_dict(self):
        return dict(id=self.id,
                    marker=self.marker)

class Nucleotide(db.Model):
    __tablename__ = 'nucleotides'
    id = db.Column(db.Integer, server_default=text("nextval('nucleotides_id_seq')"), primary_key=True)
    marker_id = db.Column(db.Integer, db.ForeignKey('markers.id'), nullable=False)
    sequence = db.Column(db.String, nullable=False)
    marker_wise_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return dict(id=self.id,
                    marker_id=self.marker_id,
                    sequence=self.sequence,
                    marker_wise_id=self.marker_wise_id)

class CondensedProfile(db.Model):
    __tablename__ = 'condensed_profiles'
    #     "CREATE TABLE condensed_profiles (id INTEGER PRIMARY KEY,"
    #     " sample_name text, coverage float, taxonomy_id INTEGER);\n")
    id = db.Column(db.Integer, server_default=text("nextval('condensed_profiles_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    coverage = db.Column(db.Float, nullable=False, index=True)
    filled_coverage = db.Column(db.Float, nullable=False, index=True)
    # relative_abundance is a filled coverage
    relative_abundance = db.Column(db.Float, nullable=False, index=True)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), nullable=False, index=True)
    taxonomy_type = db.Column(db.String, nullable=False, index=True)

    # domain_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # phylum_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # class_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # order_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # family_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # genus_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # species_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)

    ncbi_metadata = db.relationship("NcbiMetadata", back_populates="condensed_profiles")
    taxonomy = db.relationship("Taxonomy", back_populates="condensed_profiles", foreign_keys=[taxonomy_id])


class CondensedProfileCtas1(db.Model):
    '''Materialized subset of CondensedProfile for taxonomy search performance.'''
    __tablename__ = 'condensed_profiles_ctas1'
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), primary_key=True, index=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), primary_key=True, index=True)
    relative_abundance = db.Column(db.Float, nullable=False, index=True)
    filled_coverage = db.Column(db.Float, nullable=False, index=True)


class Taxonomy(db.Model):
    # Not used here but this is the logical place to put it since it is used in the condensed profile
    # taxonomy_level_columns = ['domain_id','phylum_id','class_id','order_id','family_id','genus_id','species_id']

    #     "CREATE TABLE taxonomies (id INTEGER PRIMARY KEY, taxonomy_level TEXT, parent_id INTEGER, name TEXT); \n"
    __tablename__ = 'taxonomies'
    id = db.Column(db.Integer, server_default=text("nextval('taxonomies_id_seq')"), primary_key=True)
    taxonomy_level = db.Column(db.String, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), nullable=True)
    name = db.Column(db.String, nullable=False, index=True)
    full_name = db.Column(db.String, nullable=False)
    taxonomy_type = db.Column(db.String, nullable=False, index=True)
    host_sample_count = db.Column(db.Integer)
    ecological_sample_count = db.Column(db.Integer)

    condensed_profiles = db.relationship('CondensedProfile', back_populates='taxonomy', foreign_keys=[CondensedProfile.taxonomy_id])
    # condensed_profile_domains = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.domain_id])
    # condensed_profile_phyla = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.phylum_id])
    # condensed_profile_classes = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.class_id])
    # condensed_profile_orders = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.order_id])
    # condensed_profile_families = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.family_id])
    # condensed_profile_genera = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.genus_id])
    # condensed_profile_species = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.species_id])

    def to_dict(self):
        return dict(id=self.id,
                    taxonomy_level=self.taxonomy_level,
                    parent_id=self.parent_id,
                    name=self.name)

    def split_taxonomy(self):
        return self.full_name.split('; ')

class BiosampleAttribute(db.Model):
    __tablename__ = 'biosample_attributes'
    id = db.Column(db.Integer, server_default=text("nextval('biosample_attributes_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    k = db.Column(db.String, nullable=False, index=True)
    v = db.Column(db.String, nullable=False)
    
    def to_dict(self):
        return dict(id=self.id,
                    run_id=self.run_id,
                    k=self.k,
                    v=self.v)

class ParsedSampleAttribute(db.Model):
    __tablename__ = 'parsed_sample_attributes'
    id = db.Column(db.Integer, server_default=text("nextval('parsed_sample_attributes_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    collection_year = db.Column(db.Integer)
    collection_month = db.Column(db.Integer)
    latitude = db.Column(db.Float, index=True)
    longitude = db.Column(db.Float, index=True)
    depth = db.Column(db.Float)
    temperature = db.Column(db.Float)
    host_or_not_prediction = db.Column(db.String)
    host_or_not_recorded = db.Column(db.String)
    host_or_not_mature = db.Column(db.String)
    # sample  bacterial_archaeal_bases        metagenome_size read_fraction   warning
    bacterial_archaeal_bases = db.Column(db.Float)
    # metagenome_size = db.Column(db.Float) #=> use mbases from ncbi_metadata
    smf = db.Column(db.Float)
    smf_warning = db.Column(db.Boolean)
    known_species_fraction = db.Column(db.Float)
    globdb_known_species_fraction = db.Column(db.Float)
    low_complexity = db.Column(db.Boolean)
    top1_order_fraction = db.Column(db.Float)
    top3_order_fraction = db.Column(db.Float)
    # Backend classification flags (populated in generate_backend_db). Strict T/F,
    # never NULL except the domain_only_* pair which is NULL when no profile was
    # loaded for that sample under the given taxonomy.
    non_metagenome_organism_strict = db.Column(db.Boolean)
    non_metagenome_organism_loose = db.Column(db.Boolean)
    synthetic = db.Column(db.Boolean)
    rna_or_non_dna_strict = db.Column(db.Boolean)
    rna_or_non_dna_loose = db.Column(db.Boolean)
    domain_only_gtdb = db.Column(db.Boolean)
    domain_only_globdb = db.Column(db.Boolean)
    domain_only_both = db.Column(db.Boolean)
    # --- BEGIN metalog meta_ columns (generated; see metaup_sandpiper) ---
    # Auto-generated from the metaup_sandpiper slim file header. All metalog
    # extended-metadata fields, stored as String (source data is heterogeneous,
    # e.g. '0-0.1', 'unknown'). Populated by the parsed_metadata stage when
    # METALOG_EXTENSION_METADATA is configured; NULL otherwise. Regenerate with
    # scripts/gen_meta_columns.py if the metalog schema changes.
    meta_blood_group = db.Column(db.String)
    meta_description = db.Column(db.String)
    meta_dol_range = db.Column(db.String)
    meta_drug_antibiotic_last3y = db.Column(db.String)
    meta_field_nominal_c = db.Column(db.String)
    meta_other_meds = db.Column(db.String)
    meta_acetate_um = db.Column(db.String)
    meta_added_matter = db.Column(db.String)
    meta_age_category = db.Column(db.String)
    meta_age_days = db.Column(db.String)
    meta_age_months = db.Column(db.String)
    meta_age_range = db.Column(db.String)
    meta_age_years = db.Column(db.String)
    meta_alkalinity = db.Column(db.String)
    meta_ammonium_mg_l = db.Column(db.String)
    meta_ammonium_um = db.Column(db.String)
    meta_amy1cn = db.Column(db.String)
    meta_antibiotic = db.Column(db.String)
    meta_antibiotic_dosage = db.Column(db.String)
    meta_artificial = db.Column(db.String)
    meta_available_info = db.Column(db.String)
    meta_birth_country = db.Column(db.String)
    meta_birth_gestational_age_weeks = db.Column(db.String)
    meta_birth_mode = db.Column(db.String)
    meta_birth_term_status = db.Column(db.String)
    meta_birth_weight_kg = db.Column(db.String)
    meta_bmi = db.Column(db.String)
    meta_bmi_range = db.Column(db.String)
    meta_bristol_stool_scale = db.Column(db.String)
    meta_butyrate_um = db.Column(db.String)
    meta_calcium_mg_l = db.Column(db.String)
    meta_captivity_status = db.Column(db.String)
    meta_captivity_status_full = db.Column(db.String)
    meta_carbon_dioxide_um = db.Column(db.String)
    meta_cause_of_death = db.Column(db.String)
    meta_chloride_mg_l = db.Column(db.String)
    meta_climatic_zone = db.Column(db.String)
    meta_cohort = db.Column(db.String)
    meta_collection_date = db.Column(db.String)
    meta_collection_date_end = db.Column(db.String)
    meta_common_timepoint = db.Column(db.String)
    meta_comorbidities = db.Column(db.String)
    meta_couple_id = db.Column(db.String)
    meta_couple_timepoint = db.Column(db.String)
    meta_cultivation_condition = db.Column(db.String)
    meta_cultivation_duration = db.Column(db.String)
    meta_days_since_antibiotics = db.Column(db.String)
    meta_days_since_fmt = db.Column(db.String)
    meta_depth_meters = db.Column(db.String)
    meta_diet = db.Column(db.String)
    meta_diet_full = db.Column(db.String)
    meta_dissolved_organic_carbon_um = db.Column(db.String)
    meta_dissolved_oxygen_um = db.Column(db.String)
    meta_doi = db.Column(db.String)
    meta_donor_d0 = db.Column(db.String)
    meta_donor_d28 = db.Column(db.String)
    meta_elevation_meters = db.Column(db.String)
    meta_enriched_soil = db.Column(db.String)
    meta_environment_biome = db.Column(db.String)
    meta_environment_feature = db.Column(db.String)
    meta_environment_material = db.Column(db.String)
    meta_environmental_package = db.Column(db.String)
    meta_ethnicity = db.Column(db.String)
    meta_family = db.Column(db.String)
    meta_ferric_iron_um = db.Column(db.String)
    meta_ferrous_iron_um = db.Column(db.String)
    meta_ferrous_um = db.Column(db.String)
    meta_filtration_lower_threshold = db.Column(db.String)
    meta_filtration_lower_threshold_kda = db.Column(db.String)
    meta_filtration_lower_threshold_um = db.Column(db.String)
    meta_filtration_upper_threshold_um = db.Column(db.String)
    meta_fmt_donor = db.Column(db.String)
    meta_food_name = db.Column(db.String)
    meta_formate_um = db.Column(db.String)
    meta_full_description = db.Column(db.String)
    meta_geographic_location = db.Column(db.String)
    meta_gestational_age_weeks = db.Column(db.String)
    meta_gestational_state = db.Column(db.String)
    meta_group = db.Column(db.String)
    meta_height_cm = db.Column(db.String)
    meta_hip_cm = db.Column(db.String)
    meta_host = db.Column(db.String)
    meta_host_common_name = db.Column(db.String)
    meta_host_scientific_name = db.Column(db.String)
    meta_host_tax_id = db.Column(db.String)
    meta_host_tax_scientific_name = db.Column(db.String)
    meta_housing_lab = db.Column(db.String)
    meta_hydrosulfide_um = db.Column(db.String)
    meta_infant_id = db.Column(db.String)
    meta_intervention = db.Column(db.String)
    meta_intervention_full = db.Column(db.String)
    meta_iron_mg_l = db.Column(db.String)
    meta_iron_um = db.Column(db.String)
    meta_isolation_source = db.Column(db.String)
    meta_land_use_category = db.Column(db.String)
    meta_land_use_full = db.Column(db.String)
    meta_last_change = db.Column(db.String)
    meta_latitude = db.Column(db.String)
    meta_lifestyle = db.Column(db.String)
    meta_linked_to = db.Column(db.String)
    meta_location = db.Column(db.String)
    meta_location_name = db.Column(db.String)
    meta_location_resolution = db.Column(db.String)
    meta_longitude = db.Column(db.String)
    meta_magnesium_mg_l = db.Column(db.String)
    meta_manganese_um = db.Column(db.String)
    meta_mean_annual_precipitation_mm = db.Column(db.String)
    meta_mean_annual_temperature = db.Column(db.String)
    meta_medical_history_notduringstudy = db.Column(db.String)
    meta_medical_operation = db.Column(db.String)
    meta_medication = db.Column(db.String)
    meta_medication_full = db.Column(db.String)
    meta_medication_with_parents = db.Column(db.String)
    meta_medicinal_plant = db.Column(db.String)
    meta_menopausal_status = db.Column(db.String)
    meta_methane_um = db.Column(db.String)
    meta_nitrate_mg_l = db.Column(db.String)
    meta_nitrate_nitrite_um = db.Column(db.String)
    meta_nitrate_um = db.Column(db.String)
    meta_nitrite_mg_l = db.Column(db.String)
    meta_nitrite_um = db.Column(db.String)
    meta_nitrogen_dioxide_um = db.Column(db.String)
    meta_nitrogen_percent = db.Column(db.String)
    meta_note = db.Column(db.String)
    meta_original_sample_name = db.Column(db.String)
    meta_original_timepoint = db.Column(db.String)
    meta_oxygen_um = db.Column(db.String)
    meta_ph = db.Column(db.String)
    meta_ph_range = db.Column(db.String)
    meta_phenotypic_information = db.Column(db.String)
    meta_phosphate_um = db.Column(db.String)
    meta_phosphorus_mg_l = db.Column(db.String)
    meta_phosphorus_um = db.Column(db.String)
    meta_plant = db.Column(db.String)
    meta_pmid = db.Column(db.String)
    meta_pooled_individuals = db.Column(db.String)
    meta_potassium_mg_l = db.Column(db.String)
    meta_pregnancy_week = db.Column(db.String)
    meta_pregnant = db.Column(db.String)
    meta_probiotic = db.Column(db.String)
    meta_propionate_um = db.Column(db.String)
    meta_protocol_label = db.Column(db.String)
    meta_provider = db.Column(db.String)
    meta_range_days_since_abxs = db.Column(db.String)
    meta_range_days_since_antibiotics = db.Column(db.String)
    meta_range_days_since_medication = db.Column(db.String)
    meta_recipient_donor = db.Column(db.String)
    meta_salinity = db.Column(db.String)
    meta_salinity_ppm = db.Column(db.String)
    meta_salinity_ppt = db.Column(db.String)
    meta_sample_alias = db.Column(db.String)
    meta_sample_collection_timepoint = db.Column(db.String)
    meta_sample_description = db.Column(db.String)
    meta_sample_title = db.Column(db.String)
    meta_sampling_campaign = db.Column(db.String)
    meta_sampling_platform = db.Column(db.String)
    meta_sampling_site = db.Column(db.String)
    meta_sampling_station = db.Column(db.String)
    meta_sex = db.Column(db.String)
    meta_silicate_um = db.Column(db.String)
    meta_site_description = db.Column(db.String)
    meta_skin_site_type = db.Column(db.String)
    meta_smoker = db.Column(db.String)
    meta_sodium_mg_l = db.Column(db.String)
    meta_specific_material = db.Column(db.String)
    meta_stool_consistency = db.Column(db.String)
    meta_strain = db.Column(db.String)
    meta_study_accession = db.Column(db.String)
    meta_study_code = db.Column(db.String)
    meta_subject_disease_status = db.Column(db.String)
    meta_subject_disease_status_full = db.Column(db.String)
    meta_subject_id = db.Column(db.String)
    meta_sulfate_mg_l = db.Column(db.String)
    meta_sulfate_um = db.Column(db.String)
    meta_sulfide_um = db.Column(db.String)
    meta_synbiotic = db.Column(db.String)
    meta_tax_id = db.Column(db.String)
    meta_temperature = db.Column(db.String)
    meta_temperature_range = db.Column(db.String)
    meta_time_period = db.Column(db.String)
    meta_timepoint = db.Column(db.String)
    meta_timepoint_note = db.Column(db.String)
    meta_timeseries_available = db.Column(db.String)
    meta_timeseries_count = db.Column(db.String)
    meta_timeseries_duration = db.Column(db.String)
    meta_tissue_type = db.Column(db.String)
    meta_total_dissolved_nitrogen_um = db.Column(db.String)
    meta_total_iron_um = db.Column(db.String)
    meta_total_manganese_um = db.Column(db.String)
    meta_total_nitrate = db.Column(db.String)
    meta_total_organic_carbon = db.Column(db.String)
    meta_type_of_birth = db.Column(db.String)
    meta_vaccine_name = db.Column(db.String)
    meta_vaginal_ph = db.Column(db.String)
    meta_vegetation = db.Column(db.String)
    meta_vegetation_full = db.Column(db.String)
    meta_village = db.Column(db.String)
    meta_waist_cm = db.Column(db.String)
    meta_water_depth_meters = db.Column(db.String)
    meta_weight_kg = db.Column(db.String)
    # --- END metalog meta_ columns ---
    # Backend-only classification flags (not surfaced on the website; intentionally
    # excluded from to_displayable_dict). Populated in the 'tags' stage by
    # add_metagenome_classification_flags() in bin/generate_backend_db.
    non_metagenome_organism_strict = db.Column(db.Boolean)
    non_metagenome_organism_loose = db.Column(db.Boolean)
    synthetic = db.Column(db.Boolean)
    rna_or_non_dna_strict = db.Column(db.Boolean)
    rna_or_non_dna_loose = db.Column(db.Boolean)
    # Per-taxonomy "nothing assigned below domain-level" flags (backend-only,
    # excluded from to_displayable_dict). Profile-derived, so they differ by
    # taxonomy_type. domain_only_gtdb / domain_only_globdb are set during the
    # stage2 condensed loads in fill_condensed_and_taxonomy_tables(); NULL means
    # no profile was loaded for that sample under that taxonomy. domain_only_both
    # = domain_only_gtdb AND domain_only_globdb, derived in the 'tags' stage.
    domain_only_gtdb = db.Column(db.Boolean)
    domain_only_globdb = db.Column(db.Boolean)
    domain_only_both = db.Column(db.Boolean)
    def to_displayable_dict(self):
        return dict(
            collection_year=self.collection_year,
            collection_month=self.collection_month,
            latitude=self.latitude,
            longitude=self.longitude,
            depth=self.depth,
            temperature=self.temperature,
            host_or_not_prediction=self.host_or_not_prediction,
            host_or_not_recorded=self.host_or_not_recorded,
            host_or_not_mature=self.host_or_not_mature,
            bacterial_archaeal_bases=self.bacterial_archaeal_bases,
            smf=self.smf,
            smf_warning=self.smf_warning,
            known_species_fraction=self.known_species_fraction,
            globdb_known_species_fraction=self.globdb_known_species_fraction,
            low_complexity=self.low_complexity,
            top1_order_fraction=self.top1_order_fraction,
            non_metagenome_organism_strict=self.non_metagenome_organism_strict,
            non_metagenome_organism_loose=self.non_metagenome_organism_loose,
            synthetic=self.synthetic,
            rna_or_non_dna_strict=self.rna_or_non_dna_strict,
            rna_or_non_dna_loose=self.rna_or_non_dna_loose,
            domain_only_gtdb=self.domain_only_gtdb,
            domain_only_globdb=self.domain_only_globdb,
            domain_only_both=self.domain_only_both)
            top1_order_fraction=self.top1_order_fraction,
            non_metagenome_organism_strict=self.non_metagenome_organism_strict,
            non_metagenome_organism_loose=self.non_metagenome_organism_loose,
            synthetic=self.synthetic,
            rna_or_non_dna_strict=self.rna_or_non_dna_strict,
            rna_or_non_dna_loose=self.rna_or_non_dna_loose,
            domain_only_gtdb=self.domain_only_gtdb,
            domain_only_globdb=self.domain_only_globdb,
            domain_only_both=self.domain_only_both)


class StudyLink(db.Model):
    __tablename__ = 'study_links'
    id = db.Column(db.Integer, server_default=text("nextval('study_links_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    study_id = db.Column(db.String)
    database = db.Column(db.String)
    label = db.Column(db.String)
    url = db.Column(db.String)

    def to_displayable_dict(self):
        if self.database:
            return dict(
                study_id=self.study_id,
                database=self.database)
        else:
            return dict(
                label=self.label,
                url=self.url)


class NcbiMetadata(db.Model):
    __tablename__ = 'ncbi_metadata'
    id = db.Column(db.Integer, server_default=text("nextval('ncbi_metadata_id_seq')"), primary_key=True)
    # acc,
    # assay_type,
    # center_name,
    # experiment,
    # sample_name,
    # instrument,
    # libraryselection,
    # librarysource,
    # platform,
    # sample_acc,
    # biosample,
    # organism,
    # sra_study,
    # releasedate,
    # bioproject,
    # avgspotlen,
    # mbases,
    # insertsize,
    # library_name,
    # biosamplemodel_sam,
    # collection_date_sam,
    # geo_loc_name_country_calc,
    # geo_loc_name_country_continent_calc,
    # geo_loc_name_sam,
    # sample_name_sam,
    # attributes
    acc = db.Column(db.String, nullable=False, index=True)
    assay_type = db.Column(db.String)
    center_name = db.Column(db.String)
    experiment = db.Column(db.String, index=True)
    sample_name = db.Column(db.String)
    model = db.Column(db.String)
    librarylayout = db.Column(db.String)
    libraryselection = db.Column(db.String)
    librarysource = db.Column(db.String)
    platform = db.Column(db.String)
    sample_acc = db.Column(db.String, index=True)
    biosample = db.Column(db.String, index=True)
    taxon_name = db.Column(db.String)
    sra_study = db.Column(db.String, index=True)
    published = db.Column(db.DateTime)
    bioproject = db.Column(db.String, index=True)
    # mbytes = db.Column(db.Integer)
    # avgspotlen = db.Column(db.Integer)
    bases = db.Column(db.BigInteger)
    spots = db.Column(db.BigInteger)
    insertsize = db.Column(db.Integer)
    library_name = db.Column(db.String)
    collection_date_parsed = db.Column(db.DateTime)
    geo_loc_name_country_calc = db.Column(db.String)
    geo_loc_name_country_continent_calc = db.Column(db.String)
    geo_loc_name = db.Column(db.String)
    ena_first_public_run = db.Column(db.String)
    ena_last_update_run = db.Column(db.String)

    # Below are fields found from kingfisher annotate
    experiment_title = db.Column(db.String)
    library_strategy = db.Column(db.String)
    organisation_name = db.Column(db.String)
    organisation_department = db.Column(db.String)
    organisation_institution = db.Column(db.String)
    organisation_street = db.Column(db.String)
    organisation_city = db.Column(db.String)
    organisation_country = db.Column(db.String)
    organisation_contact_name = db.Column(db.String)
    study_title = db.Column(db.String, index=True) # Index because /project matches via title when abstract is not available
    study_abstract = db.Column(db.String, index=True) # Index for /project
    design_description = db.Column(db.String)
    read1_length_average = db.Column(db.Float)
    read1_length_stdev = db.Column(db.Float)
    read2_length_average = db.Column(db.Float)
    read2_length_stdev = db.Column(db.Float)

    study_links = db.relationship('StudyLink', backref='ncbi_metadata', foreign_keys=[StudyLink.run_id])
    biosample_attributes = db.relationship('BiosampleAttribute', backref='ncbi_metadata', foreign_keys=[BiosampleAttribute.run_id])
    condensed_profiles = db.relationship('CondensedProfile', back_populates='ncbi_metadata', foreign_keys=[CondensedProfile.run_id])
    parsed_sample_attributes = db.relationship('ParsedSampleAttribute', backref='ncbi_metadata', foreign_keys=[ParsedSampleAttribute.run_id])

    def to_displayable_dict(self):
        biosample_attrs = [x for x in self.biosample_attributes if x.k != 'primary_search']
        # Temporary fix - somehow study_links are in the wrong table atm. HACK!!
        study_links_tmp = [x.v for  x in biosample_attrs if x.k == 'study_links']
        print('tmp: '+str(study_links_tmp)+' type is '+str(type(study_links_tmp)))
        # study_links_tmp currently a list of str e.g. ([{"db": "pubmed", "id": "29669589"}])
        # convert to list of dicts
        study_links = [study_link.to_displayable_dict() for study_link in self.study_links]
        for sl0 in study_links_tmp:
            try:
                print("Evaluating study_links sl0: "+str(sl0))
                sl = eval(sl0)
                for s in sl:
                    if 'id' in s:
                        s['study_id'] = s['id']
                        del s['id']
                    if 'db' in s:
                        s['database'] = s['db']
                        del s['db']
                    if 'label' in s:
                        s['label'] = s['label']
                    if 'url' in s:
                        s['url'] = s['url']
                    study_links.append(s)
            except Exception as e:
                print(f"Error parsing study_links: {e}")
        return dict(acc=self.acc,
                    assay_type=self.assay_type,
                    center_name=self.center_name,
                    experiment=self.experiment,
                    sample_name=self.sample_name,
                    model=self.model,
                    librarylayout=self.librarylayout,
                    libraryselection=self.libraryselection,
                    librarysource=self.librarysource,
                    platform=self.platform,
                    sample_acc=self.sample_acc,
                    biosample=self.biosample,
                    taxon_name=self.taxon_name,
                    sra_study=self.sra_study,
                    releasedate=self.published.strftime('%-d %B %Y') if self.published else None,
                    bioproject=self.bioproject,
                    # bytes=self.bytes,
                    # loaddate=self.loaddate,
                    # avgspotlen=self.avgspotlen,
                    bases=self.bases,
                    spots=self.spots,
                    insertsize=self.insertsize,
                    library_name=self.library_name,
                    collection_date_parsed=self.collection_date_parsed.strftime('%-d %B %Y') if self.collection_date_parsed else None,
                    geo_loc_name_country_calc=self.geo_loc_name_country_calc,
                    geo_loc_name_country_continent_calc=self.geo_loc_name_country_continent_calc,
                    geo_loc_name=self.geo_loc_name,
                    ena_first_public_run=self.ena_first_public_run,
                    ena_last_update_run=self.ena_last_update_run,
                    experiment_title=self.experiment_title,
                    library_strategy=self.library_strategy,
                    organisation_department=self.organisation_department,
                    organisation_institution=self.organisation_institution,
                    organisation_street=self.organisation_street,
                    organisation_city=self.organisation_city,
                    organisation_country=self.organisation_country,
                    organisation_contact_name=self.organisation_contact_name,
                    study_title=self.study_title,
                    study_abstract=self.study_abstract,
                    design_description=self.design_description,
                    read1_length_average=self.read1_length_average,
                    read1_length_stdev=self.read1_length_stdev,
                    read2_length_average=self.read2_length_average,
                    read2_length_stdev=self.read2_length_stdev,
                    study_links=study_links,
                    biosample_attributes=[{'k': x.k, 'v': x.v} for x in self.biosample_attributes if x.k != 'primary_search'],
                    parsed_sample_attributes=self.parsed_sample_attributes[0].to_displayable_dict())

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, server_default=text("nextval('tags_id_seq')"), primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False)

    def to_displayable_dict(self):
        return dict(
            name=self.name,
            description=self.description)

class RunTag(db.Model):
    __tablename__ = 'run_tags'
    id = db.Column(db.Integer, server_default=text("nextval('run_tags_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)

    def to_displayable_dict(self):
        return dict(
            run_id=self.run_id,
            tag_id=self.tag_id)


class SandpiperCache(db.Model):
    __tablename__ = 'sandpiper_cache'
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.Text, nullable=False)
