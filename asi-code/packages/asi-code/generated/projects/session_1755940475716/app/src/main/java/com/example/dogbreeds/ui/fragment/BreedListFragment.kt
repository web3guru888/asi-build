package com.example.dogbreeds.ui.fragment

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.DividerItemDecoration
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.dogbreeds.R
import com.example.dogbreeds.data.model.DogBreed
import com.example.dogbreeds.ui.adapter.BreedListAdapter
import com.example.dogbreeds.ui.viewmodel.BreedListViewModel
import com.example.dogbreeds.util.NetworkMonitor
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.google.android.material.snackbar.Snackbar

/**
 * Fragment to display a list of dog breeds.
 * Supports both linear and grid layout presentation.
 * Retrieves data from API or local cache depending on network availability.
 */
class BreedListFragment : Fragment() {

    private lateinit var viewModel: BreedListViewModel
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: BreedListAdapter
    private lateinit var fabToggleLayout: FloatingActionButton
    private lateinit var networkMonitor: NetworkMonitor

    private var isGridMode = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.activity_main, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupViewModel()
        setupViews(view)
        setupRecyclerView()
        setupNetworkMonitor()
        setupFab()

        observeData()
        fetchBreedList()
    }

    private fun setupViewModel() {
        viewModel = ViewModelProvider(this)[BreedListViewModel::class.java]
    }

    private fun setupViews(view: View) {
        recyclerView = view.findViewById(R.id.recyclerView)
        fabToggleLayout = view.findViewById(R.id.fabToggleLayout)
    }

    private fun setupRecyclerView() {
        adapter = BreedListAdapter { breed ->
            navigateToBreedDetail(breed)
        }

        recyclerView.apply {
            setHasFixedSize(true)
            adapter = this@BreedListFragment.adapter
            addItemDecoration(DividerItemDecoration(context, LinearLayoutManager.VERTICAL).apply {
                ContextCompat.getDrawable(context, R.drawable.divider)?.let { divider ->
                    setDrawable(divider)
                }
            })
        }

        updateLayoutManager()
    }

    private fun setupNetworkMonitor() {
        networkMonitor = NetworkMonitor(context = requireContext())
        networkMonitor.start { isConnected ->
            if (isConnected) {
                viewModel.refreshBreedList()
            } else {
                showNetworkWarning()
            }
        }
    }

    private fun setupFab() {
        fabToggleLayout.setOnClickListener {
            isGridMode = !isGridMode
            updateLayoutManager()
            updateFabIcon()
        }
        updateFabIcon()
    }

    private fun updateLayoutManager() {
        val spanCount = if (isGridMode) 2 else 1
        val orientation = if (isGridMode) LinearLayoutManager.VERTICAL else GridLayoutManager.VERTICAL
        val layoutManager = if (isGridMode) {
            GridLayoutManager(context, spanCount)
        } else {
            LinearLayoutManager(context, orientation, false)
        }
        recyclerView.layoutManager = layoutManager
        adapter.setViewType(if (isGridMode) BreedListAdapter.VIEW_TYPE_GRID else BreedListAdapter.VIEW_TYPE_LIST)
    }

    private fun updateFabIcon() {
        val iconRes = if (isGridMode) R.drawable.ic_list else R.drawable.ic_grid
        fabToggleLayout.setImageDrawable(ContextCompat.getDrawable(requireContext(), iconRes))
        fabToggleLayout.contentDescription = if (isGridMode) "Switch to list view" else "Switch to grid view"
    }

    private fun observeData() {
        viewModel.breeds.observe(viewLifecycleOwner) { result ->
            when (result) {
                is com.example.dogbreeds.data.Result.Success -> {
                    adapter.submitList(result.data)
                    if (result.data.isEmpty()) {
                        showEmptyState()
                    }
                }
                is com.example.dogbreeds.data.Result.Error -> {
                    showError(result.exception.message)
                }
                is com.example.dogbreeds.data.Result.Loading -> {
                    // Optional: show loading indicator
                }
            }
        }
    }

    private fun fetchBreedList() {
        if (networkMonitor.isConnected()) {
            viewModel.fetchBreedList()
        } else {
            viewModel.loadCachedBreeds()
            showNetworkWarning()
        }
    }

    private fun navigateToBreedDetail(breed: DogBreed) {
        val action = BreedListFragmentDirections.actionBreedListToBreedDetail(breed)
        findNavController().navigate(action)
    }

    private fun showError(message: String?) {
        val errorMsg = message ?: "An unexpected error occurred"
        Toast.makeText(context, "Error: $errorMsg", Toast.LENGTH_LONG).show()
    }

    private fun showNetworkWarning() {
        view?.let { v ->
            Snackbar.make(v, "No internet connection. Showing cached data.", Snackbar.LENGTH_INDEFINITE)
                .setAction("Retry") {
                    if (networkMonitor.isConnected()) {
                        viewModel.refreshBreedList()
                    }
                }
                .show()
        }
    }

    private fun showEmptyState() {
        // Optional: handle empty state
        Toast.makeText(context, "No breeds found", Toast.LENGTH_SHORT).show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        networkMonitor.stop()
    }
}