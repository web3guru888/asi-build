package com.example.dogbreeds.ui.viewmodel

import androidx.lifecycle.*
import com.example.dogbreeds.data.repository.BreedRepository
import com.example.dogbreeds.domain.model.Breed
import com.example.dogbreeds.domain.model.BreedDetail
import com.example.dogbreeds.util.Result
import kotlinx.coroutines.launch
import timber.log.Timber

class BreedViewModel(private val breedRepository: BreedRepository) : ViewModel() {

    // LiveData to hold list of breeds
    private val _breeds = MutableLiveData<Result<List<Breed>>>()
    val breeds: LiveData<Result<List<Breed>>> = _breeds

    // LiveData to hold detailed breed information
    private val _breedDetail = MutableLiveData<Result<BreedDetail>>()
    val breedDetail: LiveData<Result<BreedDetail>> = _breedDetail

    // LiveData for search query
    private val _searchQuery = MutableLiveData<String>()
    val searchQuery: LiveData<String> = _searchQuery

    // Filtered list of breeds based on search
    val filteredBreeds: LiveData<List<Breed>> = Transformations.switchMap(_breeds) { result ->
        Transformations.map(_searchQuery) { query ->
            when (result) {
                is Result.Success -> {
                    if (query.isNullOrEmpty()) {
                        result.data
                    } else {
                        result.data.filter { breed ->
                            breed.name.contains(query, ignoreCase = true)
                        }
                    }
                }
                else -> emptyList()
            }
        }
    }

    init {
        fetchBreeds()
    }

    /**
     * Fetch list of dog breeds from repository
     */
    fun fetchBreeds() {
        _breeds.value = Result.Loading
        viewModelScope.launch {
            try {
                val breedList = breedRepository.getBreeds()
                _breeds.value = Result.Success(breedList)
            } catch (e: Exception) {
                Timber.e(e, "Error fetching breeds")
                _breeds.value = Result.Error(e)
            }
        }
    }

    /**
     * Fetch detailed information about a specific breed by ID
     * @param breedId The ID of the breed
     */
    fun fetchBreedDetail(breedId: String) {
        _breedDetail.value = Result.Loading
        viewModelScope.launch {
            try {
                val detail = breedRepository.getBreedDetail(breedId)
                _breedDetail.value = Result.Success(detail)
            } catch (e: Exception) {
                Timber.e(e, "Error fetching breed detail for breedId: $breedId")
                _breedDetail.value = Result.Error(e)
            }
        }
    }

    /**
     * Update search query
     * @param query The new search query
     */
    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    /**
     * Toggle favorite status of a breed
     * @param breed The breed to update
     */
    fun toggleFavorite(breed: Breed) {
        viewModelScope.launch {
            try {
                breed.isFavorite = !breed.isFavorite
                breedRepository.updateFavoriteStatus(breed.id, breed.isFavorite)
            } catch (e: Exception) {
                Timber.e(e, "Failed to update favorite status for breed: ${breed.id}")
                // Optionally revert UI state or notify user on error
            }
        }
    }
}