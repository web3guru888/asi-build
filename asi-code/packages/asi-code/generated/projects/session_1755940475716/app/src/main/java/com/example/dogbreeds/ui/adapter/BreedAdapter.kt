package com.example.dogbreeds.ui.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.dogbreeds.data.model.Breed
import com.example.dogbreeds.databinding.ItemBreedBinding
import com.example.dogbreeds.databinding.ItemBreedGridBinding

class BreedAdapter(
    private val isGrid: Boolean = false,
    private val onItemClick: (Breed) -> Unit,
    private val onFavoriteToggle: (Breed) -> Unit
) : ListAdapter<Breed, BreedAdapter.BreedViewHolder>(BreedDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BreedViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (isGrid) {
            val binding = ItemBreedGridBinding.inflate(inflater, parent, false)
            GridViewHolder(binding, onItemClick, onFavoriteToggle)
        } else {
            val binding = ItemBreedBinding.inflate(inflater, parent, false)
            ListViewHolder(binding, onItemClick, onFavoriteToggle)
        }
    }

    override fun onBindViewHolder(holder: BreedViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    abstract class BreedViewHolder(private val binding: androidx.viewbinding.ViewBinding) : RecyclerView.ViewHolder(binding.root) {
        open fun bind(item: Breed) {}
    }

    class ListViewHolder(
        private val binding: ItemBreedBinding,
        private val onItemClick: (Breed) -> Unit,
        private val onFavoriteToggle: (Breed) -> Unit
    ) : BreedViewHolder(binding) {

        override fun bind(item: Breed) {
            binding.apply {
                breedName.text = item.name
                breedOrigin.text = item.origin ?: "Unknown origin"
                breedDescription.text = item.description ?: "No description available."
                favoriteIcon.isSelected = item.isFavorite

                root.setOnClickListener { onItemClick(item) }
                favoriteIcon.setOnClickListener {
                    onFavoriteToggle(item)
                    favoriteIcon.isSelected = !favoriteIcon.isSelected
                }

                // Accessibility
                breedName.contentDescription = "Dog breed name: ${item.name}"
                favoriteIcon.contentDescription = if (item.isFavorite) "Remove from favorites" else "Add to favorites"
            }
        }
    }

    class GridViewHolder(
        private val binding: ItemBreedGridBinding,
        private val onItemClick: (Breed) -> Unit,
        private val onFavoriteToggle: (Breed) -> Unit
    ) : BreedViewHolder(binding) {

        override fun bind(item: Breed) {
            binding.apply {
                breedName.text = item.name
                favoriteIcon.isSelected = item.isFavorite

                root.setOnClickListener { onItemClick(item) }
                favoriteIcon.setOnClickListener {
                    onFavoriteToggle(item)
                    favoriteIcon.isSelected = !favoriteIcon.isSelected
                }

                // Accessibility
                breedName.contentDescription = "Dog breed: ${item.name}"
                favoriteIcon.contentDescription = if (item.isFavorite) "Remove from favorites" else "Add to favorites"
            }
        }
    }

    class BreedDiffCallback : DiffUtil.ItemCallback<Breed>() {
        override fun areItemsTheSame(oldItem: Breed, newItem: Breed): Boolean = oldItem.id == newItem.id
        override fun areContentsTheSame(oldItem: Breed, newItem: Breed): Boolean = oldItem == newItem
    }
}